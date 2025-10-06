from google.adk.agents import BaseAgent, LlmAgent, InvocationContext
from collections.abc import AsyncGenerator
from typing import override
from google.adk.events import Event
from pydantic import BaseModel, Field
import json
from common.common import remove_json_tags
from google.adk.planners import BuiltInPlanner
from google.genai import types
from common.common import EXTRACTED_ENTITY,  GIST_OUTPUT_KEY, NEXT_AGENT, LAST_DB_RESULTS, CURRENT_QUERY_ENTITY, update_session_state, set_state_after_tool_call
from google.adk.agents.readonly_context import ReadonlyContext
from .prompts.systempPrompt import system_prompt

from db.search_engine import find_by_discovery, find_by_eligibility, modify_course_result, vector_search



def getEntityExtractory(state):
    x = state.get(EXTRACTED_ENTITY, {})
    try:
        gist =  json.loads(remove_json_tags( state.get(GIST_OUTPUT_KEY, "")))
        gist = gist.get("gist", "")
    except Exception as e:
        print(f"Error in parsing gist {e}")
        gist = ""
    instructions = f'''You are expert enity extractor for india education system.
**Task**
From the current user query extract the entities. Note that some entities may not pre present in current request.

**Context**
program level is "UG"


last extracted entities: {x}
gist so far: {gist}


**Entities to be extracted.**
1. **query_text** (str): 
    The user's natural language query.

2. **course_stream_type**
    In india there are various types of courses offered based on stream user is pursuing.
    **THIS MUST BE A LIST OF STRINGS FROM BELOW POSSIBLE VALUES**
    MCA, BCA, B.Tech, BA, MBA, LLB, D.Pharmacy, B.Com, BBA, M.Tech, IntegratedLaw, B.Sc, B.Pharmacy
    *Examples
        a) User asks for "engineering and management courses". You should extract ["BE/B.Tech", "BBA", "MBA"].
        b) User asks for "science courses". You should extract ["B.Sc", "M.Sc"].

3. **qualification**
    The last qualification user has finished 
    **Possible Values**
    "Certificate course", "B.Sc.", "Diploma", "Graduate", "Bachelor's Degree", "B.C.A", "10+2", "M. Sc.", "B.E./B.Tech", "D.Voc"( diploma of vocational courses)
    *Examples
        a) Show me undergraduat courses
        b) Show me post graduat courses.
        c) show me courses. 

4. *subjects**
    The subjects which user has opted in the last qualification
    
5. **stream**
    In indian eductaion system student opts stream in which he wants to pursue higher studies. They are
    arts, commerce, medical and non medical.
    if stream is non medical then assign [Mathematics, Physics, Chemistry] to subject
    if stream is medical then assign [ Biology, Physics, Chemistry] to subject

6.  *percentage**
    Percentage obtained by user.

Return Example:
{{
    "query_text" : <User query>
    "program_level": "UG",
    "course_stream_type": <Return a list of strings here. e.g., ["B.Sc", "B.E./B.Tech"]>
    "qualification": <The last qualification user has finished>
    "subjects": [list of subjects opted by user]
    "stream": <stream opted by user>
    "agentId": <Hardcoded 2>
    "purpose": <Fuuny take on your purpose. Also let user know that it will take time to finish the task so be patient.>
}}




'''
    return LlmAgent(
        name="extract_order_entity",
        model="gemini-2.5-flash",
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=False,
                thinking_budget=0,
            )
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=1,
            response_mime_type="application/json"
        ),
        instruction=instructions,
        output_key=CURRENT_QUERY_ENTITY
    )


def auto_agent_instruction(context: ReadonlyContext):
    entity = context.state.get(EXTRACTED_ENTITY, {})
    last_db_results = context.state.get(LAST_DB_RESULTS, [])
    instr = f'''You are and expert career councillor. 

<Task>
    Your task is to help student find a correct undergraduate course.   
</Task>


<Context>
Pathway: {system_prompt}
</Context>

<Information>
    extracted_entity = {entity}
    last_db_results_present = {len(last_db_results) > 0}
</Information>


<Tools>
    1. **`find_by_eligibility(criteria (dict))`**: 
        Arguments:
            criteria (dict): 
                'qualification', 'percentage', 'stream', 'subjects' (list), 'specialization'.
                extracted_entity and current_query_entity will have required information.
            tenant_id (str): The ID of the client tenant.
        Return Value:
            List of course names for which user is eligible.
        
        criteria (dict): A dictionary with keys 'qualification', 
                         'percentage', 'stream', 'subjects', 'specialization'.

    2. **`find_by_discovery(criteria: dict)`**: 
        Arguments:
            criteria (dict): 
                Compulsory Keys:         
                    query_text (str): The user's natural language query.
                    program_level (str): level for which course is being discovered. Must be either UG or PG
                    course_stream_type (list[str], optional): A list of program types the user is searching for.
                Optional Keys: 'qualification', 'percentage', 'stream', 'subjects' (list), 'specialization'.
                extracted_entity and current_query_entity will have required information.
            tenant_id (str): The ID of the client tenant.
        Return Value:
            List of courses for selected course_categories
    3. **`vector_search`**: 
        Arguments:
            query (str): user query
            tenant_id (str): The ID of the client tenant.

        Return Value:
            A list of strings, where each string returns the chunk of text which matches user query
            similarity score and url from where text was scraped. 
        
        Use this tool to search anything other than courses.
    
</Tools>

<Flow>
    Step 1. Identify the path way for graduation
    Step 2. Show the courses based on required pathway
    Step 3. Guide student to choose correct course.
    Step 4. Keep on suggesting/asking questions till user has selected a course.
</Flow>


'''
    return instr



def auto_agent():
    agent = LlmAgent(
            name="auto",
            model="gemini-2.5-flash",
            instruction=auto_agent_instruction,
            sub_agents=[],
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=False,
                    thinking_budget=-1 
                )
            ),
            generate_content_config=types.GenerateContentConfig(
                temperature=1
            ),
            output_key = GIST_OUTPUT_KEY,
            tools=[
                    find_by_eligibility, 
                    find_by_discovery,
                    vector_search
            ],
            after_tool_callback=modify_course_result,

        )
    return agent




class AutoAgent(BaseAgent, BaseModel):
    class Config:
        arbitrary_types_allowed = True

    name: str = Field(default='auto_controller')
    def __init__(self, **data):
        BaseModel.__init__(self, **data)
        BaseAgent.__init__(self, name=self.name, sub_agents=[])

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        x = getEntityExtractory(ctx.session.state)
        async for event in x.run_async(ctx):
            yield event
        
            # Merge the current entity into the main extracted entity.
        existing_entity_str = ctx.session.state.get(EXTRACTED_ENTITY, '{}')
        existing_entity = json.loads(remove_json_tags(existing_entity_str))
        
        current_entity_str = ctx.session.state.get(CURRENT_QUERY_ENTITY, '{}')
        current_entity = json.loads(remove_json_tags(current_entity_str))
        
        existing_entity.update(current_entity)
        
        await update_session_state(EXTRACTED_ENTITY, json.dumps(existing_entity), ctx.session, ctx.session_service)
        auto = auto_agent()
        async for event in auto.run_async(ctx):
            yield event




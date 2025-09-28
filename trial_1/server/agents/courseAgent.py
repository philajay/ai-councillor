from google.adk.agents import BaseAgent, LlmAgent, InvocationContext
from collections.abc import AsyncGenerator
from typing import override
from google.adk.events import Event
from google.adk.planners import BuiltInPlanner
from google.genai import types
from pydantic import BaseModel, Field
import json
from db.search_engine import find_by_discovery, modify_course_result
from common.common import remove_json_tags
from google.adk.agents.readonly_context import ReadonlyContext
from common.common import GIST_OUTPUT_KEY, EXTRACTED_ENTITY, LAST_DB_RESULTS , update_session_state, SHOW_SUGGESTED_QUESTIONS, LLM_PROCESSED_DB_RESULTS, set_state_after_tool_call, LAST_CLIENT_MESSAGE, CURRENT_QUERY_ENTITY, remove_json_tags


def getEntityExtractor(state):
    x = state.get(EXTRACTED_ENTITY, {})
    try:
        gist =  json.loads(remove_json_tags( state.get(GIST_OUTPUT_KEY, "")))
        gist = gist.get("gist", "")
    except Exception as e:
        print(f"Error in parsing gist {e}")
        gist = ""
    instructions = f'''You are expert enity extractor for india education system.
**Task**
From the current user query extract the entities. If program_level is not mentioned ask user politely to mention the program_level.

**Context**
In indian education system bsc, bca, bcom are bachelor progmanss. So their program level is 'ug'
Msc, Mca, Mcom are master programs. So their program level is 'pg'

You also have access to last entities extracted and summary of conversation till now under gist.

last extracted entities: {x}
gist so far: {gist}


**Entities to be extracted.**

1. **program_level**
    program level for which user is exploring courses. 
    **Possible Values**
    It can be either 'ug' or 'pg'
    *Examples
        a) Show me undergraduate courses
        b) Show me post graduatd courses.
        c) show me courses. 
    **Note**
    Sometime user will not directly mention 'ug' or 'pg'. They will mention their last qualification from which you need to infer if student is lookig for ug or pf course.
    For example user might say I have done my +2. In this case we can infer that user is looking for ug courses.

2. *course_stream_type**
    In india there are various types of courses offered based on stream user is pursuing.
    **THIS MUST BE A LIST OF STRINGS.**
    **Possible Values**
    It can be either "MCA", "BCA", "BA", "BE/B.Tech", "B.Pharm", "LLB", "BBA/BMS", "BA/BBA LLB", "MBA/PGDM", "B.Com", "D.El.Ed", "ME/M.Tech", "B.Sc"
    *Examples
        a) User asks for "engineering and management courses". You should extract ["BE/B.Tech", "BBA/BMS", "MBA/PGDM"].
        b) User asks for "science courses". You should extract ["B.Sc", "M.Sc"].
3. **topic**
    Subject for which user is looking for courses. Note that there can be None/multiple subjects.
    **Possible Values**
    Examples: 
    a) I want to do course in data science. -> "data science"
    b) Compaer courses in bsc and bca in air -> "ai"
    c) I want to do course in data science and ai -> "data science", "ai"
        
**Constraints**
- If program_level is not mentioned ask user politry about the program_level. 
- `course_stream_type` must be a JSON array of strings, e.g., `["B.Sc", "BE/B.Tech"]`. If only one is found, it should still be in an array, e.g., `["BCA"]`. If none are found, return an empty array `[]`.


We will always follow **this Chain of Thoughts:**
1) if program_level is missing, ask user politely about program_level.
{{
    "agentId": <Hardcoded 2>
    "program_level": <level>,
    "course_stream_type": [],
    "topic": <string>,
    "clarification_question": <Question to get the program_level>
    "reason_for_clarification": <Reason why you are asking this question.>'
}}

2) if program_level is present return json 
    {{
        "program_level": <level>,
        "course_stream_type": <Return a list of strings here. e.g., ["B.Sc", "B.E./B.Tech"]>
        "topic": <string>,
        "agentId": <Hardcoded 2>
        "purpose": <Fuuny take on your purpose. Also let user know that it will take time to finish the task so be patient.>
    }}

IMPORTANT:
- Never ever make assumptions about program_level. If it is not mentioned in query or cannot be inferred from last qualification, ask user politely to mention it.

'''
    return LlmAgent(
        name="extract_order_entity",
        model="gemini-2.5-flash-lite",
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



def course_discovery_instruction(context: ReadonlyContext):
    entity = context.state.get(EXTRACTED_ENTITY, {})
    x = json.loads(remove_json_tags(entity))
    topic = x.get("topic", "")
    if not topic:
        topic = context.state.get(LAST_CLIENT_MESSAGE, "")
    instruction =  f'''You are and expert education consultant whoc is expert in interpreting the course details.
**Task**
Provide insights to students about courses based on their query. 

Extracted Entities: {entity}
query_text = {topic}

You have access to the following tool:
1.  **`find_by_discovery(filters: list)`**: 
    Arguments:
    query_text (str): The user's natural language query.
    program_level (str): level for which course is being discovered. Must be either ug or pg
    course_stream_type (str, optional): The program type user is searching for, e.g., BE/Btech, bsc. Defaults to None.

    This tool returns the courses based on user query, program_level and course_stream_type entity.

    
Tool call returns the list of courses to user also which user can see.

**Guidelines**
Based on query and tool call results provide insights to user about the courses.
Insights should be relevant to curses and should help user in taking decision.


'''
    return instruction


def course_discovery():
    return LlmAgent(
        name="find_by_discovery",
        model="gemini-2.5-flash-lite",
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=False,
                thinking_budget=0,
            )
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=1
        ),
        instruction=course_discovery_instruction,
        tools=[find_by_discovery],
        after_tool_callback=set_state_after_tool_call,
        output_key=LLM_PROCESSED_DB_RESULTS
    )


class CourseAgent(BaseAgent, BaseModel):
    name: str = Field(default='root_intent_classifier')
    #extract_entities: LlmAgent = Field(default_factory=getEntityExtractor)
    # name: str = 'root_intent_classifier'
    # agent_to_run: LlmAgent
    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **data):
        BaseModel.__init__(self, **data)
        BaseAgent.__init__(self, name=self.name, sub_agents=[])

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:


        cd = course_discovery() 
        entity = json.loads(remove_json_tags( ctx.session.state[EXTRACTED_ENTITY]))
        print(f"Entities extracted are {entity}")

        if not entity["program_level"]:
            return

        await update_session_state(SHOW_SUGGESTED_QUESTIONS, True, ctx.session, ctx.session_service)
        if  entity["program_level"]:
            async for event in cd.run_async(ctx):
                yield event
            
           

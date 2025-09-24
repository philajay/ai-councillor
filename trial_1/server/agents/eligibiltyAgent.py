from google.adk.agents import BaseAgent, LlmAgent, InvocationContext
from collections.abc import AsyncGenerator
from typing import override
from google.adk.events import Event
from google.adk.planners import BuiltInPlanner
from google.genai import types
from pydantic import BaseModel, Field
import json
from db.search_engine import find_by_eligibility
from common.common import remove_json_tags
from google.adk.agents.readonly_context import ReadonlyContext
from common.common import set_state_after_tool_call, EXTRACTED_ENTITY, DB_RESULTS, GIST_OUTPUT_KEY, remove_json_tags


def getEntityExtractor():
    instructions = '''You are expert enity extractor for india education system.
**Task**
From the current user query extract the entities. 

**Entities to be extracted.**
1. **qualification**
    The last qualification user has finished 
    **Possible Values**
    "Certificate course", "B.Sc.", "Diploma", "Graduate", "Bachelor's Degree", "B.C.A", "10+2", "M. Sc.", "B.E./B.Tech"
    *Examples
        a) Show me undergraduat courses
        b) Show me post graduat courses.
        c) show me courses. 
    **Note**

2. *subject**
    The subjects which user has opted in the last qualification
    
3. **stream**
    In indian eductaion system student opts stream in which he wants to pursue higher studies. They are
    arts, commerce, medical and non medical.
    if stream is non medical then assign Mathematics to subject
    if stream is medical then assign Biology to subject

3. *specialization**
    The course done by user in his graduation. 

4.  *percentage**
    Percentage obtained by user.
    
        
Expected output:
{{
    "agentId": 3
    "qualification": <>,
    "subject": <Return if present else return null>
    "specialization": <>
    "percentage": <>
    "stream":<>
    "purpose": <Funny take on your purpose and what are you doing. Also let user know that it will take time to finish the task so be patient.>
}}

'''
    return LlmAgent(
        name="extract_eligibility_entity",
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
        output_key=EXTRACTED_ENTITY
    )






def eligibility_instruction(context: ReadonlyContext):
    entity = context.state[EXTRACTED_ENTITY]

    gist = context.state.get(GIST_OUTPUT_KEY, '')
    print(f"gist --> {gist}")
    return f'''You are and expert education consultant.
**Task**
Answer the question using the data obtained by tool find_by_eligibility.

Extracted Entities: {entity}

You have access to the following tool:
1.  **`find_by_eligibility(criteria (dict))`**: 
    criteria (dict): A dictionary with keys 'qualification', 
                         'percentage', 'stream', 'subject', 'specialization'.

                         
'''


def eligibility():
    return LlmAgent(
        name="get_eligibility",
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
        instruction=eligibility_instruction,
        tools=[find_by_eligibility],
        after_tool_callback=set_state_after_tool_call,
        #after_tool_callback=modify_course_result,
        output_key=DB_RESULTS
    )


class EligibilityAgent(BaseAgent, BaseModel):
    name: str = Field(default='root_rligibilty_classifier')
    extract_entities: LlmAgent = Field(default_factory=getEntityExtractor)
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
        async for event in self.extract_entities.run_async(ctx):
            yield event

        entity = json.loads(remove_json_tags( ctx.session.state[EXTRACTED_ENTITY]))
        print(f"Entities extracted are {entity}")

        er = eligibility()
        async for event in er.run_async(ctx):
            yield event


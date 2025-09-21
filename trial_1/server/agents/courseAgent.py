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
from common.common import EXTRACTED_ENTITY, DB_RESULTS


def getEntityExtractor(state):
    x = state.get(EXTRACTED_ENTITY, {})
    instructions = f'''You are expert enity extractor for india education system.
**Task**
From the current user query extract the entities. If program_level is not mentioned ask user politely to mention the program_level.

**Context**
Bsc, BCa, BA etc are all bachelors progman
MSC Mca etc are all masters programs

You also have access to history of the last entities extracted.
history: {x}


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
    **Possible Values**
    It can be either "MCA", "BCA", "BA", "BE/B.Tech", "B.Pharm", "LLB", "BBA/BMS", "BA/BBA LLB", "MBA/PGDM", "B.Com", "D.El.Ed", "ME/M.Tech", "B.Sc"
    
        
**Constraints**
If program_level is not mentioned ask user politry about the program_level. 


We will always follow **this Chain of Thoughts:**
1) if program_level is missing, ask user politely about program_level.
2) if program_level is present return json 
    {{
        "program_level": <level>,
        "course_stream_type": <Return if present else return null>
        "agentId": <Hardcoded 2>
        "purpose": <Fuuny take on your purpose. Also let user know that it will take time to finish the task so be patient.>
    }}

{{
    "agentId": <Hardcoded 2>
    "program_level": <level>,
    "course_stream_type": <Return if present else return null>
    "clarification_question": <Question to get the program_level>
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
        output_key=EXTRACTED_ENTITY
    )



def course_discovery_instruction(context: ReadonlyContext):
    entity = context.state.get(DB_RESULTS, {})
    return f'''You are and expert education consultant.
**Task**
Answer the question using the data obtained by tool find_by_discovery.

Extracted Entities: {entity}

You have access to the following tool:
1.  **`find_by_discovery(filters: list)`**: This tool returns the courses based on user query and program_level entity.

Instructions:
1) Group the results logically for easy scanning.
2) Always end the response explaing why CGC is good choice for future.
'''

def course_discovery():
    return LlmAgent(
        name="get_course_info",
        model="gemini-2.5-flash",
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
        #after_tool_callback=modify_course_result,
        output_key=DB_RESULTS
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
        extract_entities = getEntityExtractor(ctx.session.state)
        async for event in extract_entities.run_async(ctx):
            yield event

        entity = json.loads(remove_json_tags( ctx.session.state[EXTRACTED_ENTITY]))
        print(f"Entities extracted are {entity}")

        if not entity["program_level"]:
            return

        if  entity["program_level"]:
            async for event in cd.run_async(ctx):
                yield event


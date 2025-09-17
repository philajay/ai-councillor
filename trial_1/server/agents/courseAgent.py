from google.adk.agents import BaseAgent, LlmAgent, InvocationContext
from collections.abc import AsyncGenerator
from typing import override
from google.adk.events import Event
from google.adk.planners import BuiltInPlanner
from google.genai import types
from pydantic import BaseModel, Field

def getEntityExtractor():
    instructions = '''You are expert enity extractor for india education system.
**Task**
From the current user query extract the entities. If program_level is not mentioned ask user politely to mention the program_level.

**Entities to be extracted.**

1. **program_level**
    program level for which user is exploring courses. 
    **Possible Values**
    It can be either 'ug' or 'pg'
    *Examples
        a) Show me undergraduat courses
        b) Show me post graduat courses.
        c) show me courses. 
    **Note**
    Sometime user will not directly mention 'ug' or 'pg'. They will mention their last qualification from which you need to infer if student is lookig for ug or pf course.
    For example user might say I have done my +2. In this case we can infer that user is looking for ug courses.

2. *course_stream_type**
    In india there are various types of courses offered based on stream user is pursuing.
    For example. In arts you can do B.A, B.A(Hons)
    in non medical user can do B.Tech, B.E. or B.Sc
    and so on. 
    You need to extract the course_stream_type B.Sc, BA, B.com, B.des  etc
    
        
**Constraints**
If program_level is not mentioned ask user politry about the program_level. 


We will always follow **this Chain of Thoughts:**
1) if program_level is missing, ask user politely about program_level.
2) if program_level is present return json 
    {
        "program_level": <level>,
        "course_stream_type": <Return if present else return null>
    }

'''
    return LlmAgent(
        name="extract_order_entity",
        model="gemini-2.0-flash",
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=False,
                thinking_budget=0,
            )
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=1,
            #response_mime_type="application/json"
        ),
        instruction=instructions,
        output_key='course__entities'
    )




class CourseAgent(BaseAgent, BaseModel):
    name: str = Field(default='root_intent_classifier')
    agent_to_run: LlmAgent = Field(default_factory=getEntityExtractor)

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
        async for event in self.agent_to_run.run_async(ctx):
            yield event

        print(f"Entities extracted are {ctx.session.state['extracted_entities']}")
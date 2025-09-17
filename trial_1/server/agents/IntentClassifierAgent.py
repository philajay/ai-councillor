from google.adk.agents import BaseAgent, LlmAgent, InvocationContext
from collections.abc import AsyncGenerator
from typing import override
from google.adk.events import Event
from google.adk.planners import BuiltInPlanner
from google.genai import types
from pydantic import BaseModel, Field

def getIntentClassifier():
    instructions = '''You and expert intent classifier in an eductional institue. 
**Task**
Using the previous context and current instruction classify the current Query.

**Types of Intent**

1. **course_discovery**
    The current query is about course. 
    *Examples
        a) What undergraduate and postgraduate courses are offered at the university?
        b) Can you provide a detailed overview of the B.Tech in Computer Science program, including its syllabus and specializations?
        c) What are the specializations available in the MBA program, and what is the curriculum for each?

2. **general**
    Any query which could not be assigned to specific intent is assigned general intent
    *Examples
        a) What is weather like at university

        
**Output**
your output should be json as shown below
{{
    "intent": <assigned intent>
}}
'''
    return LlmAgent(
        name="intent_classifier",
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
        output_key='classified_intent'
    )

class IntentClassifierAgent(BaseAgent, BaseModel):
    name: str = Field(default='root_intent_classifier')
    agent_to_run: LlmAgent = Field(default_factory=getIntentClassifier)

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
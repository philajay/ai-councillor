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

1. **course_type_discovery**
    The current query is about discovery of course. No course is present in query and user is trying to find the various course option available to user.
    *Examples
        a) Give me options after postgraduation. <user wants to see list of options to choose from.>
        b) What can I do in graduation.  <user wants to see list of options to choose from in graduation.>
            

2. **course_discovery**
    The current query is about course. One course must be present in the query.
    *Examples
        a) Tell me about courses in information technology? <In this case information technology is mentioned>
        b) What are the specializations available in the MBA program, and what is the curriculum for each? 
            <In this case MBA is mentioned>

2. **course_discovery_by_eligibility**
    Find teh courses for user using the eligibility
    *Examples
        a) What courses can I apply with 60% in 12th
        b) I have done 3 years diploma? Which courses can I apply to?

            
3. **general**
    Any query which could not be assigned to specific intent is assigned general intent
    *Examples
        a) What is weather like at university

 4. **course_details**
    The user is asking for more information about a specific course that was mentioned in the previous turn.
    *Examples
        a) Tell me more about B.Sc forencics.
        b) What are the fees for B.Tech CSE?
        
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
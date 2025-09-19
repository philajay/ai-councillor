from google.adk.agents import BaseAgent, LlmAgent, InvocationContext
from collections.abc import AsyncGenerator
from typing import override
from google.adk.events import Event
from google.adk.planners import BuiltInPlanner
from google.genai import types
from pydantic import BaseModel, Field
from common.common import GIST_OUTPUT_KEY

def get_gist_agent(state:dict):
    gist = state.get(GIST_OUTPUT_KEY, '')
    instructions = f'''You are an expert conversation summarizer.
**Task**
Your job is to summarize the gist till now with important details of this turn including the user query, any agent agent response.
gist till now: {gist}

Instructions:
1) Do not include the university specific information like 'Why is university good for you.'
2) Summary shuld never be more than 5 lines. 

'''
    return LlmAgent(
        name="gist_generator",
        model="gemini-2.5-flash",
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=False,
                thinking_budget=0,
            )
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.5,
            response_mime_type="application/json"
        ),
        instruction=instructions,
        output_key=GIST_OUTPUT_KEY
    )

class GistAgent(BaseAgent, BaseModel):
    name: str = Field(default='gist_agent')
    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **data):
        BaseModel.__init__(self, **data)
        BaseAgent.__init__(self, name=self.name, sub_agents=[])

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # This agent is designed to be called with specific inputs,
        # so its own run implementation is minimal.
        # The actual logic is in the get_gist_agent function.
        g = get_gist_agent(ctx.session.state)
        async for event in g.run_async(ctx):
            yield event

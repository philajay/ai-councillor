from google.adk.agents import BaseAgent, LlmAgent, InvocationContext
from collections.abc import AsyncGenerator
from typing import override
from google.adk.events import Event
from google.adk.planners import BuiltInPlanner
from google.genai import types
from pydantic import BaseModel, Field
from common.common import GIST_OUTPUT_KEY

def get_suggested_question(state:dict):
    instructions = f'''Generate 2-3 follow up questions based on conversation of this turn.
Question you ask must subtly persuade user to  select the course for registration by keeping questions on topic course, admission, scholarship only.   
'''
    return LlmAgent(
        name="suggested_question_generator",
        model="gemini-2.5-flash",
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=False,
                thinking_budget=0,
            )
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.5,
        ),
        instruction=instructions,
    )

class SuggestedQuestion(BaseAgent, BaseModel):
    name: str = Field(default='suggested_question_generator_agent')
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
        g = get_suggested_question(ctx.session.state)
        async for event in g.run_async(ctx):
            yield event

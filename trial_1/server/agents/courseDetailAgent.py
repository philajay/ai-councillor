from google.adk.agents import BaseAgent, LlmAgent, InvocationContext
from collections.abc import AsyncGenerator
from typing import override
from google.adk.events import Event
from google.adk.planners import BuiltInPlanner
from pydantic import BaseModel, Field
import json
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.sessions import Session
from google.genai import types
from common.common import DB_RESULTS
from db.search_engine import get_course_details_by_id, modify_course_result


def get_course_detail_agent(session: Session):
    # Retrieve the cached results from the session state
    last_results = session.state.get(DB_RESULTS, [])

    instructions = f'''You are an expert education consultant.
Your task is to provide detailed information about a specific course that the user is asking about.

**Context:**
The user was previously shown this list of courses. Each course entry is a string with comma-separated values, the first of which is the course ID.
{json.dumps(last_results, indent=2)}

You have access to the following tool:
1.  **`get_course_details_by_id(course_id: int)`**: This tool returns all details for a given course ID.

**Instructions:**
1.  First, identify which course from the context the user is referring to. They might refer to it by number (e.g., "the first one," "option 2") or by name (e.g., "the MBA program").
2.  Extract the `course_id` for that specific course from the context. The ID is the first value in the course string.
3.  Use the `get_course_details_by_id` tool with the extracted `course_id` to get the complete details.
4.  Present these details to the user in a clear, well-formatted, and comprehensive way.
5.  If you cannot determine which course the user is asking about, politely ask them to clarify. Do not use the tool if you are unsure.

In the response Highlight following:
Career Prospects:
Why choose this university:
Eligibility:
'''
    return LlmAgent(
        name="present_course_details",
        model="gemini-2.5-flash",
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=False,
                thinking_budget=0,
            )
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=1,
        ),
        instruction=instructions,
        tools=[get_course_details_by_id],
    )

class CourseDetailAgent(BaseAgent, BaseModel):
    name: str = Field(default='course_detail_agent')
    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **data):
        BaseModel.__init__(self, **data)
        BaseAgent.__init__(self, name=self.name, sub_agents=[])

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # The logic is now fully contained within the LLM agent's prompt
        detail_agent = get_course_detail_agent(ctx.session)
        async for event in detail_agent.run_async(ctx):
            yield event

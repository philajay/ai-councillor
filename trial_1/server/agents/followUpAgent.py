from google.adk.agents import BaseAgent, LlmAgent, InvocationContext
from collections.abc import AsyncGenerator
from typing import override
from google.adk.events import Event
from google.adk.planners import BuiltInPlanner
from pydantic import BaseModel, Field
import json
from google.adk.sessions import Session
from google.genai import types
from common.common import DB_RESULTS

def get_follow_up_agent(session: Session):
    # Retrieve the cached results from the session state
    last_results = session.state.get(DB_RESULTS, [])

    instructions = f'''You are an expert education consultant. Your job is to answer follow-up questions based on a list of courses that have already been shown to the user.

**Context: The Courses We Are Discussing**
The user was previously shown this list of courses. Each entry is a comma-separated string containing all known details for that course (ID, name, description, eligibility, etc.).
{json.dumps(last_results, indent=2)}
Element at index 0 contains the header with column names. Use column names to answer the questions.


**Your Task:**
1.  Carefully read the user's follow-up question.
2.  Analyze the course data provided above to find the answer. You have all the necessary information in the context.
3.  Synthesize the information and present it to the user in a clear, well-formatted, and comprehensive way.
4.  You can handle questions about a single course, multiple courses, or all of them. You can also handle comparisons.
5.  **You do not have any tools.** You must answer using only the information provided in the context. If the answer cannot be found in the context, politely state that you do not have that specific information.

**Example Follow-up Questions You Can Answer:**
- "Tell me more about the second one."
- "What is the eligibility for all of them?"
- "Compare the career prospects for the B.Tech and the B.Sc. programs."
- "What are the program highlights for the MBA?"


**Imortant Notes**
1. For any admission eligibility use column 'admission_eligibility_rules'. 
2. You are the expert. Do not refer user to any other source.
3. If you are not able to answer ask the probing question to help user.
4. If question is about admission eligibility always quote section from course data.

**Output format**
It must be markdown
-- Explain in bullet points
-- Put emphasis on important points.

'''
    return LlmAgent(
        name="answer_follow_up",
        model="gemini-2.5-flash-lite",
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
        tools=[], # Explicitly no tools
    )

class FollowUpAgent(BaseAgent, BaseModel):
    name: str = Field(default='follow_up_agent')
    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **data):
        BaseModel.__init__(self, **data)
        BaseAgent.__init__(self, name=self.name, sub_agents=[])

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # The logic is fully contained within the LLM agent's prompt
        agent = get_follow_up_agent(ctx.session)
        async for event in agent.run_async(ctx):
            yield event

from google.adk.agents import BaseAgent, LlmAgent, InvocationContext
from collections.abc import AsyncGenerator
from typing import override
from google.adk.events import Event
from pydantic import BaseModel, Field
import json
from common.common import remove_json_tags
from google.adk.tools.agent_tool import AgentTool
from google.adk.planners import BuiltInPlanner
from google.genai import types


from .IntentClassifierAgent import IntentClassifierAgent
from .courseAgent import CourseAgent
from .eligibiltyAgent import EligibilityAgent
from .followUpAgent import FollowUpAgent

from common.common import EXTRACTED_ENTITY, DB_RESULTS, GIST_OUTPUT_KEY
from .gistAgent import GistAgent



def getInstructions(state):
    ee = state.get(EXTRACTED_ENTITY, {})
    dr = state.get(DB_RESULTS, [])
    gist = state.get(GIST_OUTPUT_KEY, [])
    return f'''You are an expert conversational router for an education consultancy.
Your primary job is to analyze the user's query in the context of the conversation and delegate it to the correct specialist agent.

**Conversational Context:**
- **Last Gist:** {gist}
- **Last Database Results (`db_results`):** {"Yes, results are present." if dr else "No results yet."}

**Your Specialist Agents:**

1.  **`FollowUpAgent`**:
    - **Use Case:** Use this agent if `db_results` are present AND the user's query is a **follow-up question** about those results.
    - **Keywords:** "tell me more," "what about the second one," "compare them," "what is the eligibility," "fees for that."
    - **Example:** If the last turn showed a list of B.Tech programs and the user now asks, "What are the career prospects for them?", you MUST use this agent.

2.  **`CourseAgent`**:
    - **Use Case:** Use this agent for **new, general discovery searches** about courses. This is for when the user starts a new topic or asks a broad question.
    - **Keywords:** "show me," "tell me about," "what courses," "B.Tech," "MBA."
    - **Example:** "Show me courses in computer science."

3.  **`EligibilityAgent`**:
    - **Use Case:** Use this agent for **new, eligibility-based searches.** The user is asking what they can apply for based on their qualifications.
    - **Keywords:** "60% in 12th," "diploma," "am I eligible," "my qualifications are."
    - **Example:** "What can I study with a 3-year diploma in civil engineering?"

**Your Decision Process:**
1.  Look at the user's query.
2.  Check if `db_results` exist from a previous turn.
3.  If `db_results` exist and the query is clearly about those results, delegate to `FollowUpAgent`.
4.  Otherwise, decide if it's a new discovery search (`CourseAgent`) or a new eligibility search (`EligibilityAgent`).
5.  Delegate to the chosen agent.
'''

router_agent = None

class RouterAgent(BaseAgent, BaseModel):
    class Config:
        arbitrary_types_allowed = True

    name: str = Field(default='root_controller')
    classifier: IntentClassifierAgent = Field(default_factory=IntentClassifierAgent)
    courseAgent: CourseAgent = Field(default_factory=CourseAgent)
    eligibilityAgent: EligibilityAgent = Field(default_factory=EligibilityAgent)
    followUpAgent: FollowUpAgent = Field(default_factory=FollowUpAgent)

    def __init__(self, **data):
        BaseModel.__init__(self, **data)
        BaseAgent.__init__(self, name=self.name, sub_agents=[])

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        global router_agent
        if not router_agent:
            router_agent = LlmAgent(
                name="router",
                model="gemini-1.5-flash",
                description=getInstructions(ctx.session.state),
                sub_agents=[
                    self.followUpAgent,
                    self.courseAgent,
                    self.eligibilityAgent,
                ]
            )

        async for event in router_agent.run_async(ctx):
            yield event
        g = GistAgent()
        
        async for event in g.run_async(ctx):
            yield event
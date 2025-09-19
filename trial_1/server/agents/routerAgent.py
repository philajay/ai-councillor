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
import uuid


from .IntentClassifierAgent import IntentClassifierAgent
from .courseAgent import CourseAgent
from .eligibiltyAgent import EligibilityAgent
from .followUpAgent import FollowUpAgent

from common.common import EXTRACTED_ENTITY, DB_RESULTS, GIST_OUTPUT_KEY, NEXT_AGENT
from .gistAgent import GistAgent
from .suggestedQuestions import SuggestedQuestion
from google.adk.agents.readonly_context import ReadonlyContext


def getInstructions(context: ReadonlyContext):
    ee = context.state.get(EXTRACTED_ENTITY, {})
    dr = context.state.get(DB_RESULTS, [])
    gist = context.state.get(GIST_OUTPUT_KEY, '')
    instruction =  f'''You are an expert conversational router for an education consultancy.
Your primary job is to analyze the user's query in the context of the conversation and delegate it to the correct specialist agent.

**Conversational Context:**
- **Last Gist:** {gist}
- **Last Database Results (`db_results`):** {dr}
- **Extracted Entity:++ {ee}

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

4.  **`ClarificationAgent`**:
    - **Use Case:** Use this agent when `db_results` are present, and the user asks an eligibility-related question. This situation is ambiguous because the user might be asking about the courses already shown (`FollowUpAgent`) or starting a new, unrelated eligibility search (`EligibilityAgent`).
    - **Example:** If the last turn showed a list of B.Tech programs and the user now asks, "What can I study with 60% in 12th?", it's unclear if they mean from the list shown or in general. Use this agent to ask for clarification.

**Your Decision Process:**
1.  Look at the user's query.
2.  Check if `db_results` exist from a previous turn.
3.  If `db_results` exist and the query is clearly about those results, delegate to `FollowUpAgent`.
4.  If `db_results` exist and the user asks an eligibility question, the situation is ambiguous. Delegate to `ClarificationAgent`.
5.  Otherwise, decide if it's a new discovery search (`CourseAgent`) or a new eligibility search (`EligibilityAgent`).
6.  Delegate to the chosen agent.

output format:
{{
    "agent": <choosen agent>,
    "explanation": <Clear chain of thought as to why this agent was choosen>
}}
'''
    return instruction

def get_next_agent():
    agent = LlmAgent(
                name="router",
                model="gemini-2.5-flash",
                instruction=getInstructions,
                sub_agents=[],
                planner=BuiltInPlanner(
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=False,
                        thinking_budget=0,
                    )
                ),
                generate_content_config=types.GenerateContentConfig(
                    temperature=1
                ),
                output_key = NEXT_AGENT
            )
    return agent

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
        router_agent = get_next_agent()

        async for event in router_agent.run_async(ctx):
            yield event

        next_agent = ctx.session.state[NEXT_AGENT]
        next_agent = json.loads(remove_json_tags(next_agent))["agent"]
        
        if next_agent == "FollowUpAgent":
            print("FollowUpAgent CALLED")
            async for event in self.followUpAgent.run_async(ctx):
                yield event
        elif next_agent == "CourseAgent":
            print("CourseAgent CALLED")
            async for event in self.courseAgent.run_async(ctx):
                yield event
        elif next_agent == "EligibilityAgent":
            print("EligibilityAgent CALLED")
            async for event in self.eligibilityAgent.run_async(ctx):
                yield event
        elif next_agent == "ClarificationAgent":
            yield Event(
                author = "ClarificationAgent",
                invocation_id =  str(uuid.uuid1()),
                content =  {"parts": [{"text": "Are you asking about the eligibility for the courses we just discussed, or are you starting a new search for courses based on your eligibility?"}]},
                partial =  False,
                turn_complete =  True
            )
        # else:
        #     yield Event(
        #         type="output",
        #         data={
        #             "content": "I'm not sure how to handle that. Please try again."
        #         },
        #     )
        

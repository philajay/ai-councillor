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

from common.common import EXTRACTED_ENTITY, LLM_PROCESSED_DB_RESULTS, GIST_OUTPUT_KEY, NEXT_AGENT, LAST_DB_RESULTS
from .gistAgent import GistAgent
from .suggestedQuestions import SuggestedQuestion
from google.adk.agents.readonly_context import ReadonlyContext


def getInstructions(context: ReadonlyContext):
    ee = context.state.get(EXTRACTED_ENTITY, {})
    dr = context.state.get(LAST_DB_RESULTS, [])
    gist = context.state.get(GIST_OUTPUT_KEY, '')

    if len(dr) == 0:
        instruction =  f'''You are an expert conversational router for an education consultancy.
Your primary job is to analyze the user's query in the context of the conversation and delegate it to the correct specialist agent.

**Conversational Context:**
- **Last Gist:** {gist}
- **Extracted Entity:++ {ee}

**Your Specialist Agents:**


1.  **`CourseAgent`**:
    - **Use Case:** Use this agent for **new, general discovery searches** about courses. This is for when the user starts a new topic or asks a broad question.
    - **Keywords:** "show me," "tell me about," "what courses," "B.Tech," "MBA."
    - **Example:** "Show me courses in computer science."

2.  **`EligibilityAgent`**:
    - **Use Case:** Use this agent **only** for **new eligibility-based searches** where the user explicitly states their qualifications. The user is asking what they can apply for based on their academic background. This agent is used to query a database with columns like `qualification`, `min_percentage`, `accepted_specializations`, etc.
    - **Trigger:** The user's query MUST contain specific qualifications like:
        - "I have a diploma in..."
        - "I got 75% in my 12th grade with Physics, Chemistry, and Math."
        - "My qualification is a B.Sc. in Computer Science."
        - "I have completed my 10+2 with commerce."
    - **Keywords:** "am I eligible," "what can I study," "courses for me," "my qualifications are."
    - **Example:** "What can I study with a 3-year diploma in civil engineering?" or "I have 60% in 12th in arts,  what are my options?".
    - **IMPORTANT:** Do NOT use this agent if the user just asks "what is the eligibility for X?". That is a `FollowUpAgent` or `CourseAgent` task if it's about a specific course, or a `FollowUpAgent` if it's a follow-up to previous results. This agent is for when the user provides *their* qualifications to find *new* courses.


**Your Decision Process:**
1.  Look at the user's query.
2.  Otherwise, decide if it's a new discovery search (`CourseAgent`) or a new eligibility search (`EligibilityAgent`).
3.  Delegate to the chosen agent.

output format:
{{
    "agentId": <Send 1 as hardcoded value>
    "agent": <choosen agent>,
    "explanation": <Clear chain of thought as to why this agent was choosen>
    "purpose": <Clearly explain the purpose of agent to layman in a funny way. For Example "Im assigning the course agent to find suitable course for you. So hold your horses...". Also let user know that it will take time to finish the task so be patient. >
}}
'''
    else:
        instruction =  f'''You are an expert conversational router for an education consultancy.
Your primary job is to analyze the user's query in the context of the conversation and delegate it to the correct specialist agent.

**Conversational Context:**
- **Last Gist:** {gist}
- **Extracted Entity:++ {ee}

**Your Specialist Agents:**

1.  **`FollowUpAgent`**:
    - **Use Case:** Use this agent if `gist` is present AND the user's query is a **follow-up question** about those results.
    - **Keywords:** "tell me more," "what about the second one," "compare them," "what is the eligibility," "fees for that."
    - **Example:** If the last turn showed a list of B.Tech programs and the user now asks, "What are the career prospects for them?", you MUST use this agent.

2.  **`CourseAgent`**:
    - **Use Case:** Use this agent for **new, general discovery searches** about courses. This is for when the user starts a new topic or asks a broad question.
    - **Keywords:** "show me," "tell me about," "what courses," "B.Tech," "MBA."
    - **Example:** "Show me courses in computer science."

3.  **`EligibilityAgent`**:
    - **Use Case:** Use this agent **only** for **new eligibility-based searches** where the user explicitly states their qualifications. The user is asking what they can apply for based on their academic background. This agent is used to query a database with columns like `qualification`, `min_percentage`, `accepted_specializations`, etc.
    Carefully examine the gist and determine if we need to use this agent
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
    "agentId": <Send 1 as hardcoded value>
    "agent": <choosen agent>,
    "explanation": <Clear chain of thought as to why this agent was choosen>
    "purpose": <Clearly explain the purpose of agent to layman in a funny way. For Example "Im assigning the course agent to find suitable course for you. So hold your horses...". Also let user know that it will take time to finish the task so be patient. >
}}
'''
    return instruction


def summary_agent():
    agent = LlmAgent(
            name="router",
            model="gemini-2.5-pro",
            instruction='''You are brain of the system. Your task is to use the current gist, user request and agents available to plan how to fulfill the request. 
Agents
1)  Name: course_discovery
    - **Use Case:** Use this agent for **new, general discovery searches** about courses. This is for when the user starts a new topic or asks a broad question.
    - **Keywords:** "show me," "tell me about," "what courses," "B.Tech," "MBA."
    - **Example:** "Show me courses in computer science."
    - **Entities** Extract the entities to be used by the Agent: 
        **Context**
        Bsc, BCa, BA etc are all bachelors prog man
        MSC Mca etc are all masters programs
        **Entities to be extracted.**

        a. **program_level**
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

        b. *course_stream_type**
            In india there are various types of courses offered based on stream user is pursuing.
            **Possible Values**
            It can be either "MCA", "BCA", "BA", "BE/B.Tech", "B.Pharm", "LLB", "BBA/BMS", "BA/BBA LLB", "MBA/PGDM", "B.Com", "D.El.Ed", "ME/M.Tech", "B.Sc"
        
        Schema of entity to be passed to agent:
        {{
            "program_level": <level>,
            "course_stream_type": <Return if present else return null>
            "agentId": <Hardcoded 2>
            "purpose": <Fuuny take on your purpose. Also let user know that it will take time to finish the task so be patient.>
        }}

2 Name: EligibilityAgent
    - **Use Case:** - **Use Case:** Use this agent **only** for **new eligibility-based searches** where the user explicitly states their qualifications. The user is asking what they can apply for based on their academic background. This agent is used to query a database with columns like `qualification`, `min_percentage`, `accepted_specializations`, etc.
    - **Example:** "What can I study with a 3-year diploma in civil engineering?" or "I have 60% in 12th in arts,  what are my options?".
    - **Entities** Extract the entities to be used by the Agent: 
        **Entities to be extracted.**

        a. **qualification**
            The last qualification user has finished 
            **Possible Values**
            "Certificate course", "B.Sc.", "Diploma", "Graduate", "Bachelor's Degree", "B.C.A", "10+2", "M. Sc.", "B.E./B.Tech"
            *Examples
                a) Show me undergraduat courses
                b) Show me post graduat courses.
                c) show me courses. 
            **Note**

        b. *subject**
            The subjects which user has opted in the last qualification
            
        c. **stream**
            In indian eductaion system student opts stream in which he wants to pursue higher studies. They are
            arts, commerce, medical and non medical.
            if stream is non medical then assign [Mathematics] to subject
            if stream is medical then assign [ Biology] to subject

        d. *specialization**
            The course done by user in his graduation. 

        e.  *percentage**
            Percentage obtained by user.

        
        Schema of entity to be passed to agent:
        {{
            "agentId": 3
            "qualification": <>,
            "stream":<>
            "subject": [<Only return Subject if you are hundred percent sure>]
            "specialization": <>
            "percentage": <>
            "purpose": <Funny take on your purpose and what are you doing. Also let user know that it will take time to finish the task so be patient.>
        }}


Output Your output should be json as shown below:
{{
    "plan" : [
        {{
            "agent": <agent name>,
            "entities": <Entity object required by agent>
        }}
    ],
    "gist": <Overall Essence:
        A brief, one-to-two sentence overview of the conversation's main purpose and key takeaway.
        Main Points & Decisions:
        Use a bulleted list to highlight the most significant topics discussed.
        Clearly state any final decisions that were made.
        Key Highlights & Action Items:
        Identify and list any crucial data points, agreements, or unresolved questions.
        Enumerate all assigned action items, specifying who is responsible for each if mentioned.
    >

}}
''',
            sub_agents=[],
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=False,
                )
            ),
            generate_content_config=types.GenerateContentConfig(
                temperature=1
            ),
            output_key = GIST_OUTPUT_KEY
        )
    return agent


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
                output_key = NEXT_AGENT,
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
    suggestedQuestion: SuggestedQuestion = Field(default_factory=SuggestedQuestion)

    def __init__(self, **data):
        BaseModel.__init__(self, **data)
        BaseAgent.__init__(self, name=self.name, sub_agents=[])

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        sm = summary_agent()
        # async for event in sm.run_async(ctx):
        #     yield event
        # gist = ctx.session.state[GIST_OUTPUT_KEY]
        # view = json.loads(remove_json_tags(gist))
        # print(f"Gist is {view}")

        router_agent = get_next_agent()
        async for event in router_agent.run_async(ctx):
            yield event

        next_agent = ctx.session.state[NEXT_AGENT]
        next_agent = json.loads(remove_json_tags(next_agent))["agent"]
        
        show_suggested_questions = False

        if next_agent == "FollowUpAgent":
            print("FollowUpAgent CALLED")
            show_suggested_questions = True
            async for event in self.followUpAgent.run_async(ctx):
                yield event
        elif next_agent == "CourseAgent":
            show_suggested_questions = True
            print("CourseAgent CALLED")
            async for event in self.courseAgent.run_async(ctx):
                yield event
        elif next_agent == "EligibilityAgent":
            show_suggested_questions = True
            print("EligibilityAgent CALLED")
            async for event in self.eligibilityAgent.run_async(ctx):
                yield event
        elif next_agent == "ClarificationAgent":
            yield Event(
                author = "  ",
                invocation_id =  str(uuid.uuid1()),
                content =  {"parts": [{"text": "Are you asking about the eligibility for the courses we just discussed, or are you starting a new search for courses based on your eligibility?"}]},
                partial =  True,
            )
            yield Event(
                author = "  ",
                invocation_id =  str(uuid.uuid1()),
                content =  {"parts": [{"text": "Are you asking about the eligibility for the courses we just discussed, or are you starting a new search for courses based on your eligibility?"}]},
                partial =  False,
                turn_complete =  True
            )
        if show_suggested_questions == True:
            async for event in self.suggestedQuestion.run_async(ctx):
                yield event
        

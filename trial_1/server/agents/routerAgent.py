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
from .courseDetailAgent import CourseDetailAgent

from common.common import EXTRACTED_ENTITY, DB_RESULTS, GIST_OUTPUT_KEY
from .gistAgent import GistAgent



def getInstructions(state):
    ee = state.get(EXTRACTED_ENTITY, {})
    dr = state.get(DB_RESULTS, [])
    gist = state.get(GIST_OUTPUT_KEY, [])
    return f'''You are an expert education consultant routing queries to the correct department.                                                          
 
 You have access to details of last turn of conversation.
 Conversation: {ee} {dr}
 gist: {gist}
 
 Your job is to analyze the conversation history and user's query and delegate it to the appropriate agent.                                                                        
 You have access to the following agents:                                                                                                                 
 
 1.  **`CourseAgent`**: Use this agent when the user is asking general questions about courses, such as searching for courses by name, stream,            
      or program level (e.g., "undergraduate," "postgraduate").                                                                                           
      *   Example Queries: "Tell me about B.Tech programs," "What MBA specializations do you offer?," "Show me courses in computer science."               
                                                                                                                                                          
2.  **`EligibilityAgent`**: Use this agent when the user's query is about finding courses based on their academic qualifications, grades,                
       subjects, or percentages.                                                                                                                                
      *   Example Queries: "What can I study with 60% in my 12th-grade exams?," "I have a diploma in engineering, what are my options?," "Am I             
        eligible for the B.Sc. program?"                                                                                                                         
 
 3.  **`CourseDetailAgent`**: Use this agent when the user is asking for specific details about a course that has already been mentioned or               
      discussed in the conversation. This is for follow-up questions.                                                                                         
    *   Example Queries: "Tell me more about the first one," "What are the fees for that program?," "What is the curriculum for the B.Tech               
      CSE course we just talked about?"                                                                                                                        
                                                                                                                                                           
 Based on the user's query, decide which agent is the most appropriate and pass the control to it.                                                        
 '''                                    

# RouterAgent = LlmAgent(                                                                                                                         
#     name="router",                                                                                                                               
#     model="gemini-2.5-flash",                                                                                                                    
#     description=getInstructions(),
#     planner=BuiltInPlanner(
#             thinking_config=types.ThinkingConfig(
#                 include_thoughts=False,
#                 thinking_budget=0,
#             )
#         ),
#     generate_content_config=types.GenerateContentConfig(
#         temperature=1,
#     ),
#     sub_agents=[
#         CourseAgent(),
#         CourseDetailAgent(),
#         EligibilityAgent()
#     ]
# ) 

router_agent = None

class RouterAgent(BaseAgent, BaseModel):
    class Config:
        arbitrary_types_allowed = True

    name: str = Field(default='root_controller')
    classifier: IntentClassifierAgent = Field(default_factory=IntentClassifierAgent)
    courseAgent: CourseAgent = Field(default_factory=CourseAgent)
    eligibilityAgent: EligibilityAgent = Field(default_factory=EligibilityAgent)
    courseDetailAgent: CourseDetailAgent = Field(default_factory=CourseDetailAgent)
    # description:str = Field(default_factory=getInstructions)
    # router_agent = LlmAgent(                                                                                                                         
    #         name="router",                                                                                                                               
    #         model="gemini-2.5-flash",                                                                                                                    
    #         description=getInstructions(None),
    #         sub_agents=[
    #             courseAgent,
    #             courseDetailAgent,
    #             eligibilityAgent
    #         ]
    #     ) 

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
                model="gemini-2.5-flash",                                                                                                                    
                description=getInstructions(ctx.session.state),
                sub_agents=[
                    self.courseAgent,
                    self.courseDetailAgent,
                    self.eligibilityAgent
                ]
            ) 

        async for event in router_agent.run_async(ctx):
            yield event
        g = GistAgent()
        
        async for event in g.run_async(ctx):
            yield event
        
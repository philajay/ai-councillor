from google.adk.agents import BaseAgent, LlmAgent, InvocationContext
from collections.abc import AsyncGenerator
from typing import override
from google.adk.events import Event
from pydantic import BaseModel, Field
import json
from common.common import remove_json_tags
from google.adk.planners import BuiltInPlanner
from google.genai import types
from common.common import EXTRACTED_ENTITY,  GIST_OUTPUT_KEY, NEXT_AGENT, LAST_DB_RESULTS, CURRENT_QUERY_ENTITY, update_session_state, set_state_after_tool_call, COURSE_LEVEL
from google.adk.agents.readonly_context import ReadonlyContext
from .prompts.systempPrompt import system_prompt_UG, system_prompt_PG
from datetime import date

from db.search_engine import find_by_discovery, find_by_eligibility, modify_course_result, vector_search, get_course_details_by_id



def getEntityExtractory(state):

    features = '''Update user about one of the salient features of the university 
    ## Academic & Research Excellence
    * **NAAC A+ Accreditation:** The university holds a prestigious **NAAC A+ accreditation**, signifying excellence in various aspects of its academic journey.
    * **Research and Innovation:** A dynamic **research culture** is fostered through state-of-the-art facilities, empowering faculty and students to explore new fields and contribute to societal advancements.
    * **Experienced Faculty:** **Highly experienced and knowledgeable faculty members** provide guidance and support, fostering a strong learning environment.

    ---

    ## Infrastructure & Campus Life

    * **Modern Facilities:** The campus features **smart classrooms** with multimedia tools, **advanced technical and computer labs**, and a **Wi-Fi-enabled environment**.
    * **Lush Green Campus:** The university boasts a visually appealing, **lush green campus** that offers a conducive environment for learning.
    * **Extracurricular Activities:** A **vibrant campus life** includes a wide range of student clubs for music, dance, literature, and sports, promoting holistic development.

    ---

    ## Career Development & Opportunities

    * **100% Assured Placements:** The university prioritizes student placement with dedicated **career planning and development training**, preparing them for competitive environments.
    * **Scholarships:** Significant **scholarship opportunities**, with amounts reaching **Rs. 25 crore in 2025**, are offered to support students.
    * **International Collaborations:** The university fosters **international collaborations** through a network of universities across various countries, opening global opportunities for students.
'''


    x = state.get(EXTRACTED_ENTITY, {})
    course_level = state.get(COURSE_LEVEL, {})
    y = "undergraduate"
    if course_level == "PG":
        y = "postgraduate"
    
    instructions = f'''You are an expert entity extraction assistant. Your task is to analyze a user's query to identify and extract relevant entities. You will be given a set of "previously extracted entities" and a "new user query". Your goal is to return an updated list of all entities, incorporating entities from the new query.
**Task**
1) Primary Task: Concatenate/Replace the previously extracted queries with extracted entities from current user query.
    - replace only when query explicitly mentions interest in some entity than replace the entity.
    
2) Secondary Task: {features}

**Context**
User is looking for {y} courses. 
previous extracted entities: {x}


**Entities to be extracted.**
1. **query_text** (str): 
    The user's natural language query.

2. **program_level**
    The is always passed by client. Current value is {course_level}

3. **course_stream_type**
    In india there are various types of courses offered based on stream user is pursuing.
    **THIS MUST BE A LIST OF STRINGS FROM BELOW POSSIBLE VALUES**
    MCA, BCA, B.Tech, BA, MBA, LLB, D.Pharmacy, B.Com, BBA, M.Tech, IntegratedLaw, B.Sc, B.Pharmacy
    *Examples
        a) User asks for "engineering and management courses". You should extract ["BE/B.Tech", "BBA", "MBA"].
        b) User asks for "science courses". You should extract ["B.Sc", "M.Sc"].
    

4. **qualification**
    The last qualification user has finished 
    **Possible Values**
    "Certificate", "B.Sc.", "Diploma", "Graduate", "Bachelor's Degree", "B.C.A", "10+2", "M. Sc.", "B.E./B.Tech", "D.Voc"( diploma of vocational courses)
    *Examples
        a) Show me undergraduat courses
        b) Show me post graduat courses.
        c) show me courses. 

5. *subjects**
    The subjects which user has opted in the last qualification
    
6. **stream**
    In indian eductaion system student opts stream in which he wants to pursue higher studies. They are
    arts, commerce, medical and non medical.
    if stream is non medical then assign [Mathematics, Physics, Chemistry] to subject
    if stream is medical then assign [ Biology, Physics, Chemistry] to subject

7.  *percentage**
    Percentage obtained by user. 
    
    
Return Example:
{{
    "query_text" : <User query>
    "program_level": "As sent in by the user",
    "course_stream_type": <Return a list of strings here. e.g., ["B.Sc", "B.E./B.Tech"]>
    "qualification": <The last qualification user has finished>
    "subjects": [list of subjects opted by user]
    "stream": <stream opted by user>
    "agentId": <Hardcoded 2>
    "reason": <Explain how entities were extracted and modified the existing entities>
    "purpose": <Random trivea about university from salient features. Use you imagination to create a hook line>
}}

'''
    return LlmAgent(
        name="extract_order_entity",
        model="gemini-2.5-flash",
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=False,
                thinking_budget=0,
            )
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json"
        ),
        instruction=instructions,
        output_key=CURRENT_QUERY_ENTITY
    )


def clean_entities(entities:dict):
    to_delete = ["reason", "purpose"]
    try:
        for s in to_delete:
            del entities[s]
        return entities
    except:
        pass

def auto_agent_instruction(context: ReadonlyContext):
    entity = context.state.get(EXTRACTED_ENTITY, {})
    last_db_results = context.state.get(LAST_DB_RESULTS, [])
    entity_json =  json.loads(remove_json_tags(entity))
    entity = json.dumps(clean_entities(entity_json))

    prompt = system_prompt_UG
    if entity_json["program_level"] == "PG":
        prompt = system_prompt_PG

    instr = f'''You are and expert career councillor for "CGC University". 
Today is {date.today()}

<Agent Persona>
    Role: A friendly, knowledgeable, and encouraging course advisor.
    Tone: Professional yet warm, consultative, and aspirational. You are not a hard-seller but a career guide.
    Goal: Answer the question asked by user based solely on the chat history and data returned by tool calls . Provide reasoning behind the answer. 
</Agent Persona>

<Scholarship>
    CGC University, Mohali believes in empowering students to achieve their dreams. With the CGCUET scholarships, we’re helping you realize your full potential and ensuring you don’t miss out on any opportunity for success.
</Scholarship>




<Context>
Pathway: {prompt}
</Context>

<Information>
    extracted_entity = {entity}
    last_db_results_present = {len(last_db_results) > 0}
</Information>


<Core Principles of the Agent's Dialogue>
    1) To engage student use tool(s) to give options in terms of course types/courses to user as soon as possible in conversation. 
    2) In case you need to ask follow up question, give him options using tools and frame your question to reduce the options.
    3) Connect Data to Benefits to frame course as an investment. Be at your creative best. 
    4) Position the Scholarship Test as an Opportunity: It's not a test; it's a gateway to a more affordable, high-quality education and a chance to prove their potential.
    5) **Always Explain Your Recommendation:** Your primary role is to be a guide. You must *always* explain the 'why' behind your answer. Justify your response by connecting the information to the student's potential benefits, career path, or how it answers their specific query. This explanation is a mandatory part of every response.
</Core Principles of the Agent's Dialogue>


<Tools>
    1. **`find_by_eligibility(criteria (dict))`**: 
    Return *types of courses* which user can apply to based on the eligibility critera given by user.
    Do not ask any other question about eligibility of course types returned.
    
    Examples:
        1) What course can I apply to after doing my +2 in arts.
        In this case tool will return list for exampole ["Course Type 1", "Course Type 2"]

    Arguments:
            criteria (dict): 
                'qualification', 'percentage', 'stream', 'subjects' (list), 'specialization'.
                extracted_entity and current_query_entity will have required information.
            tenant_id (str): The ID of the client tenant.
        Return Value:
            List of course names for which user is eligible. 
        
        criteria (dict): A dictionary with keys 'qualification', 
                         'percentage', 'stream', 'subjects', 'specialization'.

    2. **`find_by_discovery(criteria: dict)`**: 
        Returns the courses strictly based on the criteria. Call this function eagerly to show choice to user as soon as possible.

        Arguments:
            criteria (dict): 
                    query_text (str): The user's natural language query.
                    program_level (str): level for which course is being discovered. Must be either UG or PG
                    course_stream_type (list[str], optional): A list of program types the user is searching for.
                    qualification (str): for program level x we might have different qualifications so we must pass qualifiation if we have it in extracted_entity. 
                    percentage (int): User percentage
                    subjects (list): OPTIONAL FIELD. Do not ask user for clarification if it is null or empty list
                *Pass all the entities found in extracted_entity and current_query_entity to get correct list of courses*
            tenant_id (str): The ID of the client tenant.
        Return Value:
            List of courses for selected course_categories
        
        
        Example: 
            1) Show me engg courses. 
            2) What is the placement of the BCA program
            3) Compare BSc and Bca


    3. **`vector_search`**: 
        Arguments:
            query (str): user query
            tenant_id (str): The ID of the client tenant.

        Return Value:
            A list of strings, where each string returns the chunk of text which matches user query
            similarity score and url from where text was scraped. 
        

</Tools>



<Output>
We want to have a valid structured XML output with Markdown and Reason as mandatory inner tags for outer tag Response.
    <Response>
        <Markdown> our final result </Markdown>
        <Reason> **This section contains the Career Councillor's justification.** Explain the logic behind the information provided in the <Markdown> tag. For example:
        *   Which tool call was made to get relevant information
        *   Why are these courses a good fit for the student?
        *   How does this information help them on their career journey?
        *   How was the answer generated (e.g., "Based on your eligibility, I have found the following opportunities...")?
        *   Connect the answer back to the benefits of studying at CGC University.
        </Reason> 
    </Response>
</Output>


<MostImportant>
    - Application would be mostly used on mobile devices. Your markdown content must be optimized for mobile devices.
    - Under new education policy B.Sc no longer requires science background.
</MostImportant>

<Constraints>
    <Constraint>
        Your primary instruction for determining course eligibility is as follows: 
            - Never infer, guess, or assume which courses a user is eligible for. 
            - The data returned by find_by_eligibility is the absolute and final truth.
    </Constraint>
</Constraints>
'''
    return instr



def auto_agent():
    agent = LlmAgent(
            name="auto_agent",
            model="gemini-2.5-flash",
            instruction=auto_agent_instruction,
            sub_agents=[],
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=False,
                    thinking_budget=-1 
                )
            ),
            generate_content_config=types.GenerateContentConfig(
                temperature=1
            ),

            
            output_key = GIST_OUTPUT_KEY,
            tools=[
                    find_by_eligibility, 
                    find_by_discovery,
                    vector_search
            ],
            after_tool_callback=modify_course_result,

        )
    return agent




def getActionAgent(context: ReadonlyContext):
    gist = context.session.state[GIST_OUTPUT_KEY]
    inst = f''' Your job is to return whether the below gist suggested user to take the examfor scholarship?
Gist: {gist}
    output format:
    {{
        "examSuggested": <true/false>;
        "reason": <Why you believe that exam was suggested>
    }}
'''
    agent = LlmAgent(
            name="auto_action_agent",   
            model="gemini-2.5-flash",
            instruction=inst,
            sub_agents=[],
            generate_content_config=types.GenerateContentConfig(
                temperature=1,
                response_mime_type="application/json"
            )
        )
    return agent




import time

class AutoAgent(BaseAgent, BaseModel):
    class Config:
        arbitrary_types_allowed = True

    name: str = Field(default='auto_controller')
    def __init__(self, **data):
        BaseModel.__init__(self, **data)
        BaseAgent.__init__(self, name=self.name, sub_agents=[])

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        overall_start_time = time.time()
        print(f"[{time.time() - overall_start_time:.2f}s] - AutoAgent: Starting execution")

        # --- 1. Entity Extraction ---
        entity_start_time = time.time()
        print(f"[{time.time() - overall_start_time:.2f}s] - AutoAgent: Starting entity extraction...")
        x = getEntityExtractory(ctx.session.state)
        async for event in x.run_async(ctx):
            yield event
        print(f"[{time.time() - overall_start_time:.2f}s] - AutoAgent: Entity extraction finished (took {time.time() - entity_start_time:.2f}s)")

        # Merge the current entity into the main extracted entity.
        existing_entity_str = ctx.session.state.get(EXTRACTED_ENTITY, '{}')
        existing_entity = json.loads(remove_json_tags(existing_entity_str))
        
        current_entity_str = ctx.session.state.get(CURRENT_QUERY_ENTITY, '{}')
        current_entity = json.loads(remove_json_tags(current_entity_str))
        
        existing_entity.update(current_entity)
        
        await update_session_state(EXTRACTED_ENTITY, json.dumps(existing_entity), ctx.session, ctx.session_service)
        
        # --- 2. Main Auto Agent ---
        auto_agent_start_time = time.time()
        print(f"[{time.time() - overall_start_time:.2f}s] - AutoAgent: Starting main auto_agent...")
        auto = auto_agent()
        async for event in auto.run_async(ctx):
            yield event
        print(f"[{time.time() - overall_start_time:.2f}s] - AutoAgent: Main auto_agent finished (took {time.time() - auto_agent_start_time:.2f}s)")

        # --- 3. Action Agent ---
        # action_agent_start_time = time.time()
        # print(f"[{time.time() - overall_start_time:.2f}s] - AutoAgent: Starting action agent...")
        # aa = getActionAgent(ctx)
        # async for event in aa.run_async(ctx):
        #     yield event
        # print(f"[{time.time() - overall_start_time:.2f}s] - AutoAgent: Action agent finished (took {time.time() - action_agent_start_time:.2f}s)")
        
        print(f"[{time.time() - overall_start_time:.2f}s] - AutoAgent: Finished execution (total took {time.time() - overall_start_time:.2f}s)")




def get_course_sales_agent(context: ReadonlyContext):
    inst = f'''You are and expert sales career councillor for "CGC University". 
Today is {date.today()}

Task:
Student browsed the courses and is looking at the details of the course. Your task is to convice him to register for scholarship exam.

<Scholarship>
    CGC University, Mohali believes in empowering students to achieve their dreams. With the CGCUET scholarships, we’re helping you realize your full potential and ensuring you don’t miss out on any opportunity for success.
</Scholarship>


<ScholarshipExamDetails>
    Two simple steps
    1: Upload Adaar card
    2: Select date and time
    3: Make payment
    4: Give example and unlock your future
</ScholarshipExamDetails>

<Agent Persona>
Role: A friendly, knowledgeable, and encouraging course advisor.
Tone: Professional yet warm, consultative, and aspirational. 
</Agent Persona>



<Core Principles of the Agent's Dialogue>
1) Connect Data to Benefits to frame couse as an investment. Be at your creative best to engage student. 
2) Position the Scholarship Test as an Opportunity: It's not a test; it's a gateway to a more affordable, high-quality education and a chance to prove their potential.
</Core Principles of the Agent's Dialogue>

<Tools>
    1. **`get_course_details_by_id(course_id:str, tenant_id:str)`**: 
    Call this function to find details of the course
    
    Arguments:
            course_id:str: 
                id of the course which student is looking for details
            tenant_id (str): The ID of the client tenant.
        Return Value:
            List of course names for which user is eligible.
        
    2. **`vector_search`**: 
        Arguments:
            query (str): user query
            tenant_id (str): The ID of the client tenant.

        Return Value:
            A list of strings, where each string returns the chunk of text which matches user query
            similarity score and url from where text was scraped. 
        

</Tools>




<Output>

your output must be in following XML Schema

<Response>
    <Markdown>
        The output should create a sense of oppurtunity and urgency by talking about the CGCUET. 
    </Markdown>
    <Reason>
        explain the reasoning for usage of the tool use if any
    </Reason>
</Response>


</Output>


<MostImportant>
    Application would be mostly used on mobile devices. Your markdown content must be optimized for mobile devices.
</MostImportant>
'''
    agent = LlmAgent(
            name="course_sales_agent",
            model="gemini-2.5-flash",
            instruction=inst,
            sub_agents=[],
            generate_content_config=types.GenerateContentConfig(
                temperature=1
            ),
            tools=[
                get_course_details_by_id,
                vector_search
            ],
        )
    return agent

class CourseSaleAgent(BaseAgent, BaseModel):
    class Config:
        arbitrary_types_allowed = True

    name: str = Field(default='course_sales_controller')
    def __init__(self, **data):
        BaseModel.__init__(self, **data)
        BaseAgent.__init__(self, name=self.name, sub_agents=[])

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        overall_start_time = time.time()
        print(f"[{time.time() - overall_start_time:.2f}s] - CourseAgent: Starting execution")

        # --- 2. Main Auto Agent ---
        auto_agent_start_time = time.time()
        print(f"[{time.time() - overall_start_time:.2f}s] - CourseAgent: Starting main auto_agent...")
        auto = get_course_sales_agent(ctx)
        async for event in auto.run_async(ctx):
            yield event
        print(f"[{time.time() - overall_start_time:.2f}s] - CourseAgent: Main auto_agent finished (took {time.time() - auto_agent_start_time:.2f}s)")






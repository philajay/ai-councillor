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

from db.search_engine import find_by_discovery, find_by_eligibility, modify_course_result, vector_search



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
    try:
        gist =  json.loads(remove_json_tags( state.get(GIST_OUTPUT_KEY, "")))
        gist = gist.get("gist", "")
    except Exception as e:
        print(f"Error in parsing gist {e}")
        gist = ""
    instructions = f'''You are expert councillor for CGC University.
**Task**
1) Primary Task: From the current user query extract the entities. Note that some entities may not pre present in current request.
Your 100% focus should be on this task
2) Secondary Task: {features}

**Context**
User is looking for {y} courses. 
last extracted entities: {x}
gist so far: {gist}


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
    "reason": <Reason why these entities were selected>
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
            temperature=1,
            response_mime_type="application/json"
        ),
        instruction=instructions,
        output_key=CURRENT_QUERY_ENTITY
    )


def clean_entities(entities:dict):
    to_delete = ["reason", "purpose"]
    for s in to_delete:
        del entities[s]
    return entities

def auto_agent_instruction(context: ReadonlyContext):
    entity = context.state.get(EXTRACTED_ENTITY, {})
    last_db_results = context.state.get(LAST_DB_RESULTS, [])
    entity_json =  json.loads(remove_json_tags(entity))
    entity = json.dumps(clean_entities(entity_json))

    prompt = system_prompt_UG
    if entity_json["program_level"] == "PG":
        prompt = system_prompt_PG

    instr = f'''You are and expert sales career councillor for "CGC University". 
Today is {date.today()}

<Agent Persona>
Role: A friendly, knowledgeable, and encouraging course advisor.
Tone: Professional yet warm, consultative, and aspirational. You are not a hard-seller; they are a career guide.
Goal: To understand the student's ambitions and show them how a specific course is the perfect vehicle to achieve those ambitions, making the scholarship test a logical and beneficial next step.
</Agent Persona>

<Scholarship>
    CGC University, Mohali believes in empowering students to achieve their dreams. With the CGCUET scholarships, we’re helping you realize your full potential and ensuring you don’t miss out on any opportunity for success.
</Scholarship>


<Core Principles of the Agent's Dialogue>
1) Connect Data to Benefits to frame couse as an investment. Be at your creative best to engage student. 
2) Position the Scholarship Test as an Opportunity: It's not a test; it's a gateway to a more affordable, high-quality education and a chance to prove their potential.
</Core Principles of the Agent's Dialogue>


<Context>
Pathway: {prompt}
</Context>

<Information>
    extracted_entity = {entity}
    last_db_results_present = {len(last_db_results) > 0}
</Information>


<Tools>
    1. **`find_by_eligibility(criteria (dict))`**: 
    Call this function to find all the types of courses which user can apply to based on the eligibility critera given by user.
    
    Examples:
        1) What course can I apply to after doing my +2 in arts.

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
        Finds courses by semantic similarity.
        Example: 
            1) Show me engg courses. 
            2) What is the placement of the BCA program
            3) Compare BSc and Bca
        Arguments:
            criteria (dict): 
                Compulsory Keys:         
                    query_text (str): The user's natural language query.
                    program_level (str): level for which course is being discovered. Must be either UG or PG
                    course_stream_type (list[str], optional): A list of program types the user is searching for.
                Optional Keys: 'qualification', 'percentage', 'stream', 'subjects' (list), 'specialization'.
                extracted_entity and current_query_entity will have required information.
            tenant_id (str): The ID of the client tenant.
        Return Value:
            List of courses for selected course_categories
    3. **`vector_search`**: 
        Arguments:
            query (str): user query
            tenant_id (str): The ID of the client tenant.

        Return Value:
            A list of strings, where each string returns the chunk of text which matches user query
            similarity score and url from where text was scraped. 
        

</Tools>

<Flow>
    Step 1. Identify the path way for graduation
    Step 2. Show the courses based on required pathway
    Step 3. Guide student to choose correct course.
    Step 4. Keep on suggesting/asking questions till user has selected a course.
</Flow>
<Output>
Output for tool find_by_discovery must always be in markdown optimized for best possible ui experience explaining why course from our university would help you get better prepared for job.
The output should create a sense of oppurtunity and urgency by talking about the CGCUET. 

</Output>


<MostImportant>
    Application would be mostly used on mobile devices. Your markdown content must be optimized for mobile devices.
</MostImportant>

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
        action_agent_start_time = time.time()
        print(f"[{time.time() - overall_start_time:.2f}s] - AutoAgent: Starting action agent...")
        aa = getActionAgent(ctx)
        async for event in aa.run_async(ctx):
            yield event
        print(f"[{time.time() - overall_start_time:.2f}s] - AutoAgent: Action agent finished (took {time.time() - action_agent_start_time:.2f}s)")
        
        print(f"[{time.time() - overall_start_time:.2f}s] - AutoAgent: Finished execution (total took {time.time() - overall_start_time:.2f}s)")




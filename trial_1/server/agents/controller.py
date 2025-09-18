from google.adk.agents import BaseAgent, LlmAgent, InvocationContext
from collections.abc import AsyncGenerator
from typing import override
from google.adk.events import Event
from pydantic import BaseModel, Field
import json
from common.common import remove_json_tags


from .IntentClassifierAgent import IntentClassifierAgent
from .courseAgent import CourseAgent


class Controller(BaseAgent, BaseModel):
    class Config:
        arbitrary_types_allowed = True

    name: str = Field(default='root_controller')
    classifier: IntentClassifierAgent = Field(default_factory=IntentClassifierAgent)
    courseAgent: CourseAgent = Field(default_factory=CourseAgent)


    def __init__(self, **data):
        BaseModel.__init__(self, **data)
        BaseAgent.__init__(self, name=self.name, sub_agents=[])

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        async for event in self.classifier.run_async(ctx):
            yield event
        print(f'Intent is {ctx.session.state["classified_intent"]}')
        intent = ctx.session.state["classified_intent"]
        intent = json.loads(remove_json_tags(intent))["intent"]
        if intent == "course_discovery":
            print("COURSE DISCOVERY CALLED")
            async for event in self.courseAgent.run_async(ctx):
                yield event
        print(f'Entities is {ctx.session.state["course__entities"]}')


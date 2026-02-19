from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from src.crews.base.llm import DEFAULT_LLM
from src.crews.tutor_router_crew.schemas import TutorMessage


@CrewBase
class TutorRouterCrew:
    """Smart Tutor router crew for language-learning chat."""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def router_manager(self) -> Agent:
        """Manager agent that interprets the user's request and plans how to respond."""
        return Agent(
            config=self.agents_config["router_manager"],
            llm=DEFAULT_LLM,
        )

    @agent
    def language_tutor(self) -> Agent:
        """General language tutor agent that can handle most language-learning requests."""
        return Agent(
            config=self.agents_config["language_tutor"],
            llm=DEFAULT_LLM,
        )

    @task
    def route_and_respond(self) -> Task:
        """Single-task flow that both routes the request and generates a structured tutor reply."""
        return Task(
            config=self.tasks_config["route_and_respond"],
            agent=self.language_tutor(),
            output_pydantic=TutorMessage,
        )

    @crew
    def crew(self) -> Crew:
        """Create the TutorRouter crew with a simple sequential process."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
        )


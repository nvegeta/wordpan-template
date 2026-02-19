"""Generic language tutor crew for grammar, writing, cultural context."""

from pathlib import Path
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from src.crews.base.llm import DEFAULT_LLM
from src.crews.tutor_router_crew.schemas import TutorMessage

_crew_dir = Path(__file__).resolve().parent


@CrewBase
class GenericTutorCrew:
    agents_config = str(_crew_dir / "config" / "generic_agents.yaml")
    tasks_config = str(_crew_dir / "config" / "generic_tasks.yaml")
    """Crew that handles grammar, writing correction, and cultural context."""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def language_tutor(self) -> Agent:
        return Agent(
            config=self.agents_config["language_tutor"],
            llm=DEFAULT_LLM,
        )

    @task
    def generic_respond(self) -> Task:
        return Task(
            config=self.tasks_config["generic_respond"],
            agent=self.language_tutor(),
            output_pydantic=TutorMessage,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
        )

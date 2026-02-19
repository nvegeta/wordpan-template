"""Translation specialist crew."""

from pathlib import Path
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from src.crews.base.llm import DEFAULT_LLM
from src.crews.tutor_router_crew.schemas import TranslationOutput

_crew_dir = Path(__file__).resolve().parent


@CrewBase
class TranslationCrew:
    agents_config = str(_crew_dir / "config" / "translation_agents.yaml")
    tasks_config = str(_crew_dir / "config" / "translation_tasks.yaml")
    """Crew that translates words/phrases with explanation."""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def translation_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["translation_specialist"],
            llm=DEFAULT_LLM,
        )

    @task
    def translate(self) -> Task:
        return Task(
            config=self.tasks_config["translate"],
            agent=self.translation_specialist(),
            output_pydantic=TranslationOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
        )

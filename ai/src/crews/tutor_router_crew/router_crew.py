"""Router crew: classifies user intent and decides routing."""

from pathlib import Path
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from src.crews.base.llm import DEFAULT_LLM
from src.crews.tutor_router_crew.schemas import RouterDecision

_crew_dir = Path(__file__).resolve().parent


@CrewBase
class RouterCrew:
    agents_config = str(_crew_dir / "config" / "router_agents.yaml")
    tasks_config = str(_crew_dir / "config" / "router_tasks.yaml")
    """Crew that classifies intent and produces a routing decision."""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def router_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["router_manager"],
            llm=DEFAULT_LLM,
        )

    @task
    def route_only(self) -> Task:
        return Task(
            config=self.tasks_config["route_only"],
            agent=self.router_manager(),
            output_pydantic=RouterDecision,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
        )

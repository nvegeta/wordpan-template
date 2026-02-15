from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from src.crews.base.llm import DEFAULT_LLM
from src.crews.similar_words_crew.schemas import SimilarWordsOutput


@CrewBase
class SimilarWordsCrew:
    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def vocabulary_assistant(self) -> Agent:
        return Agent(
            config=self.agents_config["vocabulary_assistant"],
            llm=DEFAULT_LLM,
        )

    @task
    def similar_words_task(self) -> Task:
        return Task(
            config=self.tasks_config["similar_words_task"],
            output_pydantic=SimilarWordsOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
        )

import os
from crewai import LLM

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_LLM = LLM(api_key=GROQ_API_KEY, model="groq/llama-3.3-70b-versatile")

DEFAULT_LLM = GROQ_LLM

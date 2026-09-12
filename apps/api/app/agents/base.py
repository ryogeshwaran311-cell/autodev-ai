from __future__ import annotations
from abc import ABC, abstractmethod
from app.services.gemini import GeminiService
from app.schemas import AgentResult

class Agent(ABC):
    name = "agent"

    def __init__(self, llm: GeminiService):
        self.llm = llm

    @abstractmethod
    async def run(self, context: dict) -> AgentResult:
        ...

"""Base AI provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIResult:
    """Result of an AI generation call."""

    text: str
    provider: str
    model: str
    refused: bool = False
    error: str | None = None


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""

    name: str = "base"

    @abstractmethod
    def generate(self, system: str, user: str) -> AIResult:
        """Generate a response given a system prompt and user prompt."""
        raise NotImplementedError

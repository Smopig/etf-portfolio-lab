"""Factory for selecting the active AI provider (CLAUDE.md §7)."""

from __future__ import annotations

from app.core.config import settings
from app.providers.ai.base import BaseAIProvider
from app.providers.ai.mock_provider import MockAIProvider


def get_ai_provider() -> BaseAIProvider:
    """Return the configured AI provider.

    Defaults to :class:`MockAIProvider` unless ``AI_PROVIDER=="claude"`` AND
    an Anthropic API key is configured. This ensures the feature always works
    offline / without an API key.
    """
    if settings.AI_PROVIDER == "claude":
        api_key = settings.ANTHROPIC_API_KEY or settings.CLAUDE_API_KEY
        if api_key:
            from app.providers.ai.claude_provider import ClaudeAIProvider

            return ClaudeAIProvider(api_key=api_key, model=settings.AI_MODEL)

    return MockAIProvider()

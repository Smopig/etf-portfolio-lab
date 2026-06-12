"""Claude (Anthropic API) AI provider."""

from __future__ import annotations

from app.providers.ai.base import AIResult


class ClaudeAIProvider:
    """AI provider backed by the official Anthropic SDK."""

    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-opus-4-8") -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, system: str, user: str) -> AIResult:
        try:
            import anthropic  # lazy import: optional dependency
        except ImportError as exc:
            return AIResult(
                text="",
                provider=self.name,
                model=self.model,
                refused=False,
                error=f"anthropic SDK not installed: {exc}",
            )

        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=2000,
                thinking={"type": "adaptive"},
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:  # noqa: BLE001 - surface as AIResult, not raise
            return AIResult(
                text="",
                provider=self.name,
                model=self.model,
                refused=False,
                error=f"Claude API error: {exc}",
            )

        if getattr(response, "stop_reason", None) == "refusal":
            return AIResult(
                text="",
                provider=self.name,
                model=self.model,
                refused=True,
            )

        text = "".join(
            b.text for b in response.content if getattr(b, "type", None) == "text"
        )
        return AIResult(text=text, provider=self.name, model=self.model, refused=False)

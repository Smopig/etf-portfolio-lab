"""Deterministic mock AI provider.

Default provider (CLAUDE.md §7 / works offline without API keys). Instead of
calling any LLM, it templates a structured Traditional-Chinese summary purely
from the structured ``context`` dict it is given, plus the citation block and
safety disclaimers. This guarantees by construction that answers are grounded
in system data, cite sources/dates, and include the required caveats.
"""

from __future__ import annotations

from app.providers.ai.base import AIResult

DISCLAIMER = (
    "本分析僅基於系統現有資料提供研究與風險提醒，不構成買賣建議；"
    "回測與模擬結果不代表未來績效，亦不保證未來表現。"
)


class MockAIProvider:
    """Default AI provider: deterministic, no network, grounded by construction."""

    name = "mock"

    def generate(self, system: str, user: str) -> AIResult:
        # The mock provider does not "understand" the prompt - it simply
        # echoes the structured context that was embedded in `user`,
        # followed by the mandatory citation + disclaimer block (which the
        # caller already appended). We just wrap it as the response text.
        text = (
            "【AI 分析（模擬模式 / Mock Provider）】\n\n"
            f"{user}\n\n"
            f"{DISCLAIMER}"
        )
        return AIResult(text=text, provider=self.name, model="mock-template", refused=False)

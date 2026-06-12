"""Pure numeric helpers for concentration/exposure math.

No DB access here — keep these functions easy to unit-test in isolation.
"""

from __future__ import annotations


def normalize_weights_to_fraction(weights: list[float]) -> list[float]:
    """Normalize a list of weights to fractions (0-1).

    Mirrors the scale-detection logic in
    ``app.utils.data_quality.check_holding_weight_sum``: if the sum of the
    provided weights is <= 1.5, they are assumed to already be fractions
    (e.g. 0.195 == 19.5%). Otherwise they are assumed to be percentages
    (e.g. 19.5 == 19.5%) and are divided by 100.

    Empty input returns an empty list. ``None`` values are treated as 0.
    """
    if not weights:
        return []

    cleaned = [float(w) if w is not None else 0.0 for w in weights]
    total = sum(cleaned)

    if total <= 1.5:
        return cleaned

    return [w / 100.0 for w in cleaned]


def hhi(weights_fraction: list[float]) -> float:
    """Herfindahl-Hirschman Index = sum(w^2), weights as fractions (0-1)."""
    if not weights_fraction:
        return 0.0
    return sum(w * w for w in weights_fraction)


def effective_holdings(hhi_value: float) -> float | None:
    """Effective number of holdings = 1 / HHI.

    Returns ``None`` if ``hhi_value`` is 0 (undefined / no holdings).
    """
    if not hhi_value:
        return None
    return 1.0 / hhi_value


def top_n_weight(sorted_weights: list[float], n: int) -> float:
    """Sum of the top ``n`` weights from a list already sorted descending.

    If ``n`` exceeds the length of the list, sums all available weights.
    """
    if not sorted_weights or n <= 0:
        return 0.0
    return round(sum(sorted_weights[:n]), 12)

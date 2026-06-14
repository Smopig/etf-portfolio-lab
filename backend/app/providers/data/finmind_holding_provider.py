"""FinMind ETF holdings provider (CLAUDE.md §7).

Fetches ETF constituent / holdings rows from FinMind's
``TaiwanETFHolding`` dataset. Per CLAUDE.md §7: never fabricates rows --
on failure (HTTP error, rate limit, missing token, malformed payload)
returns an empty ``records`` list with a descriptive ``errors`` entry.

Security
--------
The FinMind API token (env var ``FINMIND_API_TOKEN``) must never appear
in any output: not in ``source_url``, not in error strings, not in logs,
not in returned records. The provider strips the token before storing
the URL anywhere.

Expected payload shape
----------------------
FinMind's v4 ``/api/v4/data`` endpoint typically returns::

    {"status": 200, "data": [{...}, ...]}

Per-row field names may vary -- common aliases observed across FinMind
datasets are accepted (case-insensitive):

- stock id: ``stock_id`` / ``Code`` / ``code`` / ``security_code``
- name:     ``stock_name`` / ``Name`` / ``name``
- weight:   ``weight`` / ``Weight`` / ``percent`` / ``percentage``
- date:     ``date`` / ``Date`` / ``data_date``

If FinMind's actual schema differs, this parser will yield zero usable
rows and surface a descriptive error rather than guessing field meanings.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import time
from typing import Callable

from app.providers.data.base import BaseDataProvider, ProviderResult

DEFAULT_BASE_URL = "https://api.finmindtrade.com/api/v4/data"
DATASET = "TaiwanETFHolding"

_CODE_KEYS = {"stock_id", "code", "security_code", "asset_symbol"}
_NAME_KEYS = {"stock_name", "name", "asset_name"}
_WEIGHT_KEYS = {"weight", "percent", "percentage", "ratio"}
_DATE_KEYS = {"date", "data_date", "holding_date"}


def _default_http_get(url: str) -> bytes:
    from urllib.request import Request, urlopen

    req = Request(url, headers={"User-Agent": "etf-portfolio-lab/1.0"})
    with urlopen(req, timeout=15) as resp:  # noqa: S310
        return resp.read()


def _find_key(obj: dict, candidates: set[str]) -> str | None:
    for key in obj:
        if key.lower() in candidates:
            return key
    return None


def _redact(text: str, token: str | None) -> str:
    if not token:
        return text
    return text.replace(token, "***REDACTED***")


class FinMindHoldingProvider(BaseDataProvider):
    """Fetches ETF holdings from FinMind's ``TaiwanETFHolding`` dataset.

    Accepts an injectable ``http_get`` callable: ``(url: str) -> bytes``
    (so tests can stub the network).
    """

    name = "FinMind"
    source_type = "network"

    def __init__(
        self,
        http_get: Callable[[str], bytes] | None = None,
        base_url: str = DEFAULT_BASE_URL,
        token: str | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self.http_get = http_get or _default_http_get
        self.base_url = base_url
        # Read token at construction time (overridable for tests).
        self._token = token if token is not None else os.environ.get("FINMIND_API_TOKEN")
        self._sleep = sleeper or time.sleep

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------
    def _public_url(self, symbol: str) -> str:
        """URL safe to log / persist -- token stripped."""
        return f"{self.base_url}?dataset={DATASET}&data_id={symbol}"

    def _request_url(self, symbol: str) -> str:
        url = self._public_url(symbol)
        if self._token:
            url = f"{url}&token={self._token}"
        return url

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------
    def fetch(
        self,
        *,
        symbol: str,
        holding_date: dt.date | None = None,
        **_extra,
    ) -> ProviderResult:
        dataset_type = "etf_holdings"
        public_url = self._public_url(symbol)

        if not self._token:
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=public_url,
                data_date=None,
                reliability_level=None,
                errors=["FINMIND_API_TOKEN not set"],
            )

        raw, err = self._fetch_with_retry(symbol)
        if err is not None:
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=public_url,
                data_date=None,
                reliability_level=None,
                errors=[err],
            )

        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=public_url,
                data_date=None,
                reliability_level=None,
                errors=[f"failed to parse JSON response: {_redact(str(exc), self._token)}"],
            )

        if not isinstance(payload, dict):
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=public_url,
                errors=["unexpected payload shape (not an object)"],
            )

        status = payload.get("status")
        if status == 402 or str(status) == "402":
            # Should have been caught in _fetch_with_retry, but in case
            # FinMind returns 200 with status=402 in body:
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=public_url,
                errors=["rate_limited"],
            )

        data = payload.get("data")
        if not isinstance(data, list):
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=public_url,
                errors=["expected 'data' array in response"],
            )

        if not data:
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=public_url,
                errors=["empty data array from FinMind"],
            )

        fallback_date = holding_date or dt.date.today()
        fetched_at = dt.datetime.utcnow()
        records: list[dict] = []
        errors: list[str] = []
        max_row_date: dt.date | None = None

        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f"row {i}: not an object, skipped")
                continue
            code_key = _find_key(item, _CODE_KEYS)
            if code_key is None:
                errors.append(f"row {i}: no recognizable stock-code field, skipped")
                continue
            name_key = _find_key(item, _NAME_KEYS)
            weight_key = _find_key(item, _WEIGHT_KEYS)
            date_key = _find_key(item, _DATE_KEYS)

            weight = None
            if weight_key is not None:
                try:
                    weight = float(item[weight_key])
                except (TypeError, ValueError):
                    weight = None

            row_date: dt.date | None = None
            if date_key is not None:
                row_date = _parse_iso_date(item.get(date_key))
            effective_date = row_date or fallback_date
            if row_date is not None and (max_row_date is None or row_date > max_row_date):
                max_row_date = row_date

            records.append(
                {
                    "etf_symbol": symbol,
                    "holding_date": effective_date,
                    "asset_symbol": str(item[code_key]),
                    "asset_name": item.get(name_key) if name_key else None,
                    "weight": weight,
                    "source_name": self.name,
                    "source_url": public_url,
                    "fetched_at": fetched_at,
                    "confidence_level": "MEDIUM",
                }
            )

        if not records:
            errors.append("no usable rows parsed from response")
            return ProviderResult(
                records=[],
                dataset_type=dataset_type,
                source_name=self.name,
                source_url=public_url,
                errors=errors,
            )

        return ProviderResult(
            records=records,
            dataset_type=dataset_type,
            source_name=self.name,
            source_url=public_url,
            data_date=max_row_date or fallback_date,
            reliability_level="medium",
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Retry-aware HTTP wrapper
    # ------------------------------------------------------------------
    def _fetch_with_retry(self, symbol: str) -> tuple[bytes | None, str | None]:
        url = self._request_url(symbol)
        delays = [1.0, 2.0]  # up to 2 retries on 402
        attempts = len(delays) + 1
        last_err: str | None = None

        for attempt in range(attempts):
            try:
                raw = self.http_get(url)
            except Exception as exc:  # noqa: BLE001
                msg = _redact(str(exc), self._token)
                if _is_rate_limit_exc(exc):
                    last_err = "rate_limited"
                    if attempt < attempts - 1:
                        self._sleep(delays[attempt])
                        continue
                    return None, "rate_limited"
                return None, f"HTTP request failed: {msg}"

            if _looks_like_rate_limit_body(raw):
                last_err = "rate_limited"
                if attempt < attempts - 1:
                    self._sleep(delays[attempt])
                    continue
                return None, "rate_limited"

            return raw, None

        return None, last_err or "rate_limited"


def _is_rate_limit_exc(exc: Exception) -> bool:
    code = getattr(exc, "code", None)
    if code == 402:
        return True
    text = str(exc)
    return "402" in text


def _looks_like_rate_limit_body(raw: bytes) -> bool:
    if not raw:
        return False
    try:
        head = raw[:200].decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return False
    if '"status": 402' in head or '"status":402' in head:
        return True
    return False


def _parse_iso_date(value: object) -> dt.date | None:
    if value is None:
        return None
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None

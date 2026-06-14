"""Factory for selecting a data provider by key (mirrors ai/factory.py)."""

from __future__ import annotations

from app.providers.data.base import BaseDataProvider
from app.providers.data.csv_file_provider import CsvFileProvider, ExcelFileProvider
from app.providers.data.finmind_holding_provider import FinMindHoldingProvider
from app.providers.data.twse_etf_list_provider import TwseEtfListProvider
from app.providers.data.twse_provider import FundCompanyProvider, TwseProvider
from app.providers.data.yahoo_holding_provider import YahooHoldingProvider
from app.providers.data.yahoo_price_provider import YahooPriceProvider
from app.providers.data.yuanta_holding_provider import YuantaHoldingProvider

_PROVIDERS: dict[str, type[BaseDataProvider]] = {
    "local-file": CsvFileProvider,
    "csv": CsvFileProvider,
    "excel": ExcelFileProvider,
    "yahoo-finance": YahooPriceProvider,
    "yahoo": YahooPriceProvider,
    "twse": TwseProvider,
    "fund-company": FundCompanyProvider,
    "twse-etf-list": TwseEtfListProvider,
    "finmind-holdings": FinMindHoldingProvider,
    "yahoo-holdings": YahooHoldingProvider,
    "yuanta-holdings": YuantaHoldingProvider,
}


def get_data_provider(name: str, **cfg) -> BaseDataProvider:
    """Return an instance of the data provider registered under ``name``.

    Raises ``ValueError`` for unknown provider keys.
    """
    try:
        cls = _PROVIDERS[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown data provider '{name}'. Available: {sorted(_PROVIDERS)}"
        ) from exc
    return cls(**cfg)

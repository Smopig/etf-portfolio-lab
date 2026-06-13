"""Base data provider interface (CLAUDE.md §7).

No-fabrication contract: every :class:`ProviderResult` returned by a
:class:`BaseDataProvider` must carry ``source_name``, ``source_url``,
``data_date``, and ``reliability_level`` describing where the records came
from and how trustworthy they are. If a provider cannot obtain real data
(network failure, empty/invalid response, missing file, etc.) it MUST
return an empty ``records`` list with a descriptive entry in ``errors`` —
it must never invent, guess, or interpolate rows.
"""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ProviderResult:
    """Result of a data provider ``fetch()`` call."""

    records: list[dict] = field(default_factory=list)
    dataset_type: str = ""
    source_name: str = ""
    source_url: str | None = None
    data_date: dt.date | None = None
    reliability_level: str | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True if records were fetched without errors."""
        return bool(self.records) and not self.errors


class BaseDataProvider(ABC):
    """Abstract base class for data-source providers.

    Implementations fetch raw data (from a local file or a remote source)
    and normalize it into a list of plain dicts ready for the existing
    importer/upsert pipeline. See module docstring for the §7
    no-fabrication contract: never fabricate records, always attach source
    metadata, and report failures via ``errors`` rather than synthesizing
    data.
    """

    name: str = "base"
    source_type: str = "base"

    @abstractmethod
    def fetch(self, **params) -> ProviderResult:
        """Fetch and normalize records. Must not fabricate data on failure."""
        raise NotImplementedError

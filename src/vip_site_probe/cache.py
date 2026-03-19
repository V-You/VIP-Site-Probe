"""In-memory result cache -- holds the most recent probe output per URL."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProbeResult:
    """Container for a single tool's output."""

    url: str
    tool: str
    data: dict[str, Any]


@dataclass
class ResultCache:
    """Stores probe results per URL so follow-up actions use a coherent bucket."""

    _results_by_url: dict[str, dict[str, ProbeResult]] = field(default_factory=dict)
    _latest_url: str | None = None

    def begin(self, url: str) -> None:
        """Start a fresh result bucket for a combined probe run."""
        self._results_by_url[url] = {}
        self._latest_url = url

    def store(self, tool: str, url: str, data: dict[str, Any]) -> None:
        """Cache a probe result, keyed by tool name."""
        bucket = self._results_by_url.setdefault(url, {})
        bucket[tool] = ProbeResult(url=url, tool=tool, data=data)
        self._latest_url = url

    def get(self, tool: str, url: str | None = None) -> ProbeResult | None:
        """Retrieve cached result for a given tool, or None."""
        target_url = url or self._latest_url
        if target_url is None:
            return None
        return self._results_by_url.get(target_url, {}).get(tool)

    def get_all(self, url: str | None = None) -> list[ProbeResult]:
        """Return cached results for the latest URL bucket by default."""
        target_url = url or self._latest_url
        if target_url is None:
            return []

        bucket = self._results_by_url.get(target_url, {})
        preferred_order = ("probe_site", "check_plugins", "check_security", "probe")
        ordered = [bucket[tool] for tool in preferred_order if tool in bucket]
        extras = [result for tool, result in bucket.items() if tool not in preferred_order]
        return ordered + extras

    def last_url(self) -> str | None:
        """Return the URL from the most recently cached result."""
        return self._latest_url

    def clear(self, url: str | None = None) -> None:
        """Clear all cached results, or just one URL bucket."""
        if url is None:
            self._results_by_url.clear()
            self._latest_url = None
            return

        self._results_by_url.pop(url, None)
        if self._latest_url == url:
            self._latest_url = next(reversed(self._results_by_url), None)


# singleton instance shared across the server
cache = ResultCache()

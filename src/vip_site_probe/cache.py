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
    """Stores the most recent probe results so submit_to_zendesk can reference them."""

    _results: dict[str, ProbeResult] = field(default_factory=dict)

    def store(self, tool: str, url: str, data: dict[str, Any]) -> None:
        """Cache a probe result, keyed by tool name."""
        self._results[tool] = ProbeResult(url=url, tool=tool, data=data)

    def get(self, tool: str) -> ProbeResult | None:
        """Retrieve cached result for a given tool, or None."""
        return self._results.get(tool)

    def get_all(self) -> list[ProbeResult]:
        """Return all cached results."""
        return list(self._results.values())

    def last_url(self) -> str | None:
        """Return the URL from the most recently cached result."""
        if not self._results:
            return None
        last = list(self._results.values())[-1]
        return last.url

    def clear(self) -> None:
        """Clear all cached results."""
        self._results.clear()


# singleton instance shared across the server
cache = ResultCache()

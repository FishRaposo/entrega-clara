"""In-process metrics: counters, gauges and fixed-bucket histograms.

Deliberately tiny and dependency-free. The registry renders Prometheus text for
scrapers and a JSON snapshot for the operations panel, so both views read the
same numbers. It is process-local: counters reset on restart, which is the
honest behaviour for an in-process registry and is stated in the docs.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable
from dataclasses import dataclass, field

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

Labels = tuple[tuple[str, str], ...]


def _labels(labels: dict[str, str] | None) -> Labels:
    return tuple(sorted((labels or {}).items()))


def _render_labels(labels: Labels) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{key}="{value}"' for key, value in labels)
    return "{" + inner + "}"


@dataclass
class Histogram:
    buckets: tuple[float, ...] = BUCKETS
    counts: list[int] = field(default_factory=lambda: [0] * (len(BUCKETS) + 1))
    total: float = 0.0
    observations: int = 0

    def observe(self, value: float) -> None:
        self.total += value
        self.observations += 1
        for index, bound in enumerate(self.buckets):
            if value <= bound:
                self.counts[index] += 1
                return
        self.counts[-1] += 1


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, Labels], float] = {}
        self._gauges: dict[tuple[str, Labels], float] = {}
        self._histograms: dict[tuple[str, Labels], Histogram] = {}

    def inc(
        self, name: str, labels: dict[str, str] | None = None, value: float = 1.0
    ) -> None:
        key = (name, _labels(labels))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def set_gauge(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        with self._lock:
            self._gauges[(name, _labels(labels))] = value

    def add_gauge(
        self, name: str, delta: float, labels: dict[str, str] | None = None
    ) -> None:
        key = (name, _labels(labels))
        with self._lock:
            self._gauges[key] = self._gauges.get(key, 0.0) + delta

    def observe(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        key = (name, _labels(labels))
        with self._lock:
            histogram = self._histograms.get(key)
            if histogram is None:
                histogram = Histogram()
                self._histograms[key] = histogram
            histogram.observe(value)

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()

    def render(self) -> str:
        """Prometheus text exposition (version 0.0.4), sorted for stable diffs."""
        lines: list[str] = []
        with self._lock:
            counters = dict(self._counters)
            gauges = dict(self._gauges)
            histograms = dict(self._histograms)
        for (name, labels), value in sorted(counters.items()):
            lines += _family_header(lines, name, "counter")
            lines.append(f"{name}{_render_labels(labels)} {value:g}")
        for (name, labels), value in sorted(gauges.items()):
            lines += _family_header(lines, name, "gauge")
            lines.append(f"{name}{_render_labels(labels)} {value:g}")
        for (name, labels), histogram in sorted(histograms.items()):
            lines += _family_header(lines, name, "histogram")
            cumulative = 0
            for index, bound in enumerate(histogram.buckets):
                cumulative += histogram.counts[index]
                bucket_labels = _labels({**dict(labels), "le": _number(bound)})
                lines.append(f"{name}_bucket{_render_labels(bucket_labels)} {cumulative}")
            cumulative += histogram.counts[-1]
            infinite = _labels({**dict(labels), "le": "+Inf"})
            lines.append(f"{name}_bucket{_render_labels(infinite)} {cumulative}")
            lines.append(f"{name}_sum{_render_labels(labels)} {histogram.total:g}")
            lines.append(f"{name}_count{_render_labels(labels)} {histogram.observations}")
        return "\n".join(lines) + "\n"

    def snapshot(self) -> dict[str, list[dict[str, object]]]:
        with self._lock:
            counters = [
                {"name": name, "labels": dict(labels), "value": value}
                for (name, labels), value in sorted(self._counters.items())
            ]
            gauges = [
                {"name": name, "labels": dict(labels), "value": value}
                for (name, labels), value in sorted(self._gauges.items())
            ]
            histograms = [
                {
                    "name": name,
                    "labels": dict(labels),
                    "count": histogram.observations,
                    "sum": round(histogram.total, 6),
                }
                for (name, labels), histogram in sorted(self._histograms.items())
            ]
        return {"counters": counters, "gauges": gauges, "histograms": histograms}


def _family_header(lines: list[str], name: str, kind: str) -> Iterable[str]:
    """Emit ``# HELP``/``# TYPE`` once per metric family."""
    marker = f"# TYPE {name} {kind}"
    if marker in lines:
        return ()
    return (f"# HELP {name} Entrega Clara {kind}", marker)


def _number(value: float) -> str:
    return f"{value:g}"


METRICS = MetricsRegistry()

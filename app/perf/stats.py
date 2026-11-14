"""Per-minute request timings. The sampler copies this into perf_samples."""

import threading
import time


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * pct
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    frac = rank - low
    return float(ordered[low] * (1 - frac) + ordered[high] * frac)


class RequestStats:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latencies: list[float] = []
        self._by_path: dict[str, list[float]] = {}
        self.requests = 0
        self.errors = 0

    def record(self, path: str, status: int, milliseconds: float) -> None:
        with self._lock:
            self.requests += 1
            self._latencies.append(milliseconds)
            bucket = self._by_path.setdefault(path or "/", [])
            bucket.append(milliseconds)
            if status >= 500:
                self.errors += 1

    def snapshot(self, reset: bool = False) -> dict:
        with self._lock:
            latencies = list(self._latencies)
            by_path = {path: list(rows) for path, rows in self._by_path.items()}
            payload = {
                "request_count": self.requests,
                "error_count": self.errors,
                "latency_p50": round(percentile(latencies, 0.50), 2),
                "latency_p95": round(percentile(latencies, 0.95), 2),
                "latency_p99": round(percentile(latencies, 0.99), 2),
                "slowest": _slowest(by_path),
            }
            if reset:
                self._latencies.clear()
                self._by_path.clear()
                self.requests = 0
                self.errors = 0
            return payload


def _slowest(by_path: dict[str, list[float]]) -> list[dict]:
    rows = []
    for path, values in by_path.items():
        rows.append({"path": path, "count": len(values), "p95": round(percentile(values, 0.95), 2)})
    rows.sort(key=lambda item: item["p95"], reverse=True)
    return rows[:5]


STARTED = time.time()
STATS = RequestStats()

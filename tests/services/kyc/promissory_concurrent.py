"""Parallel promissory HTTP — one ``ApiClient`` per worker, typed API callables."""

from __future__ import annotations

import concurrent.futures as cf
import time
from collections.abc import Callable
from typing import Any

import httpx

from tests.api.client import ApiClient, ApiSide
from tests.config.settings import Settings

TRANSPORT_ATTEMPTS = 4


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((pct / 100.0) * (len(ordered) - 1)))
    return ordered[index]


def fire_concurrent_requests(
    settings: Settings,
    request_fn: Callable[[ApiClient], dict[str, Any]],
    *,
    count: int,
    workers: int,
    side: ApiSide = ApiSide.MICROSERVICE,
    auth_header: str | None = None,
) -> dict[str, Any]:
    """Fire ``count`` parallel calls of ``request_fn`` via per-worker clients.

    ``request_fn`` must use a typed API helper (route/cancel/inquiry), not a
    raw path. Transport faults are retried; server faults are returned as-is.

    Returns:
        ``{"results": [...], "summary": {total, succeeded, rejected,
        server_faults, transport_errors, min_ms, max_ms, avg_ms, p95_ms}}``.
    """

    def _one(index: int) -> dict[str, Any]:
        start = time.perf_counter()
        last_error: BaseException | None = None
        for _attempt in range(TRANSPORT_ATTEMPTS):
            try:
                with ApiClient(settings, side, auth_header) as client:
                    envelope = request_fn(client)
                elapsed = (time.perf_counter() - start) * 1000
                status = int(envelope.get("status_code") or 0)
                return {
                    "index": index,
                    "status_code": status,
                    "ok": 200 <= status < 300,
                    "elapsed_ms": round(elapsed, 1),
                    "body": envelope.get("body"),
                    "error": None,
                }
            except httpx.TransportError as exc:
                last_error = exc
                time.sleep(0.2)
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "index": index,
            "status_code": 0,
            "ok": False,
            "elapsed_ms": round(elapsed, 1),
            "body": None,
            "error": f"{type(last_error).__name__}: {last_error}",
        }

    results: list[dict[str, Any] | None] = [None] * count
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, i) for i in range(count)]
        for future in cf.as_completed(futures):
            item = future.result()
            results[item["index"]] = item

    filled: list[dict[str, Any]] = [r for r in results if r is not None]
    latencies = [float(r["elapsed_ms"]) for r in filled]
    summary = {
        "total": count,
        "succeeded": sum(1 for r in filled if r["ok"]),
        "rejected": sum(1 for r in filled if 400 <= r["status_code"] < 500),
        "server_faults": sum(1 for r in filled if 500 <= r["status_code"] < 600),
        "transport_errors": sum(1 for r in filled if r["status_code"] == 0),
        "min_ms": min(latencies) if latencies else 0,
        "max_ms": max(latencies) if latencies else 0,
        "avg_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
        "p95_ms": _percentile(latencies, 95),
    }
    return {"results": filled, "summary": summary}

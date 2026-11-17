"""Métricas Prometheus (contador, histograma de latencia) y cabecera X-Served-By."""
from __future__ import annotations

import socket
import time

from prometheus_client import Counter, Gauge, Histogram

HOSTNAME = socket.gethostname()
_HOSTNAME_BYTES = HOSTNAME.encode()

REQUESTS = Counter(
    "http_requests_total", "Peticiones HTTP atendidas", ["method", "path", "status"]
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "Latencia de las peticiones HTTP",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
IN_FLIGHT = Gauge("http_requests_in_flight", "Peticiones en curso")


class MetricsMiddleware:
    """Middleware ASGI puro (más ligero que BaseHTTPMiddleware)."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status = {"code": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-served-by", _HOSTNAME_BYTES))
                message["headers"] = headers
            await send(message)

        start = time.perf_counter()
        IN_FLIGHT.inc()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            IN_FLIGHT.dec()
            route = scope.get("route")
            path = getattr(route, "path", "unmatched")  # plantilla de ruta: evita cardinalidad alta
            method = scope["method"]
            LATENCY.labels(method, path).observe(time.perf_counter() - start)
            REQUESTS.labels(method, path, str(status["code"])).inc()

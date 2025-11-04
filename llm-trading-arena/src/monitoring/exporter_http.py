from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Dict, Optional

from .health import HealthSnapshot
from .metrics import GLOBAL_METRICS


class MonitoringHandler(BaseHTTPRequestHandler):
    metrics_supplier: Callable[[], Dict[str, object]]
    health_supplier: Callable[[], HealthSnapshot]
    kill_callback: Optional[Callable[[], None]] = None
    auth_token: Optional[str] = None
    kill_rate_limit_per_min: int = 1
    _last_kill_ts: float = 0.0

    def do_GET(self) -> None:  # type: ignore[override]
        if self.path == "/metrics.json":
            payload = json.dumps(self.metrics_supplier(), sort_keys=True).encode()
            self._respond(200, payload)
            return
        if self.path == "/health":
            payload = json.dumps(self.health_supplier().as_dict(), sort_keys=True).encode()
            self._respond(200, payload)
            return
        self._respond(404, b"")

    def do_POST(self) -> None:  # type: ignore[override]
        if self.path != "/kill" or self.kill_callback is None:
            self._respond(404, b"")
            return
        header = self.headers.get("X-Auth-Token")
        if self.auth_token and header != self.auth_token:
            self._respond(403, b"forbidden")
            return
        now = time.time()
        if now - self._last_kill_ts < 60 / max(1, self.kill_rate_limit_per_min):
            self._respond(429, b"rate limited")
            return
        self._last_kill_ts = now
        self.kill_callback()
        self._respond(200, b"kill switch engaged")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def _respond(self, status: int, payload: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)


def start_http_exporter(
    *,
    bind: str,
    port: int,
    health_supplier: Callable[[], HealthSnapshot],
    kill_callback: Optional[Callable[[], None]] = None,
    auth_token: Optional[str] = None,
    kill_rate_limit_per_min: int = 1,
) -> HTTPServer:
    handler = type(
        "_MonitoringHandler",
        (MonitoringHandler,),
        {
            "metrics_supplier": staticmethod(lambda: GLOBAL_METRICS.snapshot()),
            "health_supplier": staticmethod(health_supplier),
            "kill_callback": kill_callback,
            "auth_token": auth_token,
            "kill_rate_limit_per_min": kill_rate_limit_per_min,
        },
    )
    server = HTTPServer((bind, port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

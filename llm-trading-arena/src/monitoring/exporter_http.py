from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Dict

from .health import HealthSnapshot
from .metrics import GLOBAL_METRICS


class MonitoringHandler(BaseHTTPRequestHandler):
    metrics_supplier: Callable[[], Dict[str, float]]
    health_supplier: Callable[[], HealthSnapshot]

    def do_GET(self) -> None:  # type: ignore[override]
        if self.path == "/metrics.json":
            payload = json.dumps(self.metrics_supplier(), sort_keys=True).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/health":
            payload = json.dumps(self.health_supplier().as_dict(), sort_keys=True).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def start_http_exporter(port: int, health_supplier: Callable[[], HealthSnapshot]) -> HTTPServer:
    handler = type(
        "_MonitoringHandler",
        (MonitoringHandler,),
        {
            "metrics_supplier": staticmethod(lambda: GLOBAL_METRICS.snapshot()),
            "health_supplier": staticmethod(health_supplier),
        },
    )
    server = HTTPServer(("0.0.0.0", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

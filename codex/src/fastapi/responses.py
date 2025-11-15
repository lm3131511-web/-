from __future__ import annotations

import json
from typing import Any


class Response:
    def __init__(self, content: bytes | str = b"", *, media_type: str | None = None, status_code: int = 200) -> None:
        if isinstance(content, bytes):
            self.body = content
            self.text = content.decode("utf-8")
        else:
            self.text = content
            self.body = content.encode("utf-8")
        self.media_type = media_type or "text/plain"
        self.status_code = status_code

    def json(self) -> Any:
        return json.loads(self.text)


class JSONResponse(Response):
    def __init__(self, content: Any, *, status_code: int = 200) -> None:
        super().__init__(json.dumps(content), media_type="application/json", status_code=status_code)
        self._json = content

    def json(self) -> Any:
        return self._json


__all__ = ["Response", "JSONResponse"]

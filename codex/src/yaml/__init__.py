from __future__ import annotations

import json
from typing import Any


def safe_load(text: str) -> Any:
    return json.loads(text)

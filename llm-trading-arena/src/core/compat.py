from __future__ import annotations

import asyncio
import os
import sys
from contextlib import suppress


def maybe_install_uvloop() -> None:
    if sys.platform.startswith("linux") and os.environ.get("ARENA_NO_UVLOOP") != "1":
        with suppress(ModuleNotFoundError):
            import uvloop

            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def create_event_loop() -> asyncio.AbstractEventLoop:
    maybe_install_uvloop()
    return asyncio.new_event_loop()

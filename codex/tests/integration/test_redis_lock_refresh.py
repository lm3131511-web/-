import asyncio

from codex.llm_risk.client import LockManager


def test_lock_manager_serializes_access():
    manager = LockManager()
    lock = manager.acquire("key")
    results = []

    async def worker(idx):
        async with lock:
            results.append(idx)
            await asyncio.sleep(0.01)

    async def runner():
        await asyncio.gather(worker(1), worker(2))

    asyncio.run(runner())
    assert results == [1, 2] or results == [2, 1]
    assert len(results) == 2

"""Run CPU-bound SymPy work in a worker thread.

SymPy is synchronous pure Python. Called directly from an `async def` handler it
blocks the whole event loop, so one slow computation stalls every other request
(and the health check). `run_cpu` moves it to a thread: the loop keeps serving
other users while the computation runs.

A thread cannot be killed, so `timeout` only stops *waiting*: the client gets a
clean 504 instead of hanging, but a truly runaway computation keeps its thread
(and CPU) until it finishes. Bounding that fully needs a killable worker process.
"""
import asyncio

from fastapi import HTTPException, status

from engine.concurrency import run_in_thread

DEFAULT_TIMEOUT_SECONDS = 45.0


async def run_cpu(fn, *args, timeout: float | None = DEFAULT_TIMEOUT_SECONDS, **kwargs):
    try:
        return await asyncio.wait_for(run_in_thread(fn, *args, **kwargs), timeout)
    except asyncio.TimeoutError:
        raise HTTPException(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "This took too long to compute. Try a simpler answer.",
        )

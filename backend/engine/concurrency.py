"""Bounded worker threads for CPU-bound SymPy work (engine layer: no web imports).

SymPy is synchronous pure Python; run directly inside an `async def` it freezes the
event loop for as long as it takes. `run_in_thread` moves it to a worker thread.
At most MAX_CONCURRENT jobs run at once: SymPy is pure Python, so extra threads add
no speed, only GIL contention. Measured on 40 hard functions solves from 8 concurrent
users (main.py also sets a 1 ms GIL switch interval):

    inline (before)         14.8 s total, event loop frozen for 14.8 s
    2 workers, 1 ms switch  16.1 s total, worst loop stall 55 ms
    4 workers, 1 ms switch  26.9 s total, worst loop stall 89 ms
    4 workers, 5 ms switch  16.7 s total, worst loop stall 516 ms

(Over HTTP the switch interval trades speed for latency: see main.py.)

Note a thread cannot be killed: a runaway computation keeps its worker until it ends.
"""
import asyncio
import weakref

MAX_CONCURRENT = 2

# One semaphore per running loop (a semaphore is bound to the loop that waits on it).
_semaphores: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore]" = weakref.WeakKeyDictionary()


async def run_in_thread(fn, *args, **kwargs):
    loop = asyncio.get_running_loop()
    sem = _semaphores.get(loop)
    if sem is None:
        sem = _semaphores[loop] = asyncio.Semaphore(MAX_CONCURRENT)
    async with sem:
        return await asyncio.to_thread(fn, *args, **kwargs)

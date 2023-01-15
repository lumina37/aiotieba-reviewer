from typing import Awaitable, Callable

from ... import executor
from . import checker, filter, producer

TypeThreadsRunner = Callable[[], Awaitable[None]]


async def threads_runner(fname: str, pn: int=1) -> None:
    threads = await producer._producer(fname, pn)

    for _filter in filter._filters:
        _threads = await _filter(threads)
        if _threads is not None:
            threads = _threads

    for thread in threads:
        punish = await checker._checker(thread)
        if punish is not None:
            punish = await executor._punish_executor(punish)
            if punish is not None:
                return punish


_runner = threads_runner


def set_threads_runner(runner: TypeThreadsRunner) -> TypeThreadsRunner:
    global _runner
    _runner = runner
    return runner

from typing import Awaitable, Callable

from ... import executor
from ..._typing import Thread
from .. import post
from . import checker, filter, producer

TypeThreadsRunner = Callable[[str, int], Awaitable[None]]
TypeThreadRunner = Callable[[Thread], Awaitable[None]]


async def thread_runner(thread: Thread) -> None:
    punish = await checker._checker(thread)
    if punish is not None:
        await executor._punish_executor(punish)

    punish = await post.runner._posts_runner(thread)
    if punish is not None:
        punish.obj = thread
        await executor._punish_executor(punish)


_thread_runner = thread_runner


def set_thread_runner(runner: TypeThreadRunner) -> TypeThreadRunner:
    global _thread_runner
    _thread_runner = runner
    return runner


async def threads_runner(fname: str, pn: int = 1) -> None:
    threads = await producer._producer(fname, pn)

    for _filter in filter._filters:
        _threads = await _filter(threads)
        if _threads is not None:
            threads = _threads

    for thread in threads:
        punish = await checker._checker(thread)
        if punish is not None:
            await executor._punish_executor(punish)

        punish = await post.runner._posts_runner(thread)
        if punish is not None:
            punish
            await executor._punish_executor(punish)


_threads_runner = threads_runner


def set_threads_runner(runner: TypeThreadsRunner) -> TypeThreadsRunner:
    global _threads_runner
    _threads_runner = runner
    return runner

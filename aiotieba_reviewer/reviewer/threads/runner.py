import asyncio
from typing import Awaitable, Callable

from aiotieba import LOG

from ... import executor
from ...perf_stat import aperf_stat
from ..thread import runner
from . import filter, producer

TypeThreadsRunner = Callable[[str, int], Awaitable[None]]


async def _default_threads_runner(fname: str, pn: int = 1) -> None:

    threads = await producer.producer(fname, pn)

    for _filter in filter.filters:
        _threads = await _filter(threads)
        if _threads is not None:
            threads = _threads

    for filt in filter.filters:
        punishes = await filt(threads)
        if punishes is None:
            continue
        for punish in punishes:
            threads.remove(punish.obj)
        await asyncio.gather(*[executor.punish_executor(p) for p in punishes])

    for thread in threads:
        await runner.thread_runner(thread)


def _threads_runner_perf_stat(func: TypeThreadsRunner) -> TypeThreadsRunner:
    perf_stat = aperf_stat()

    async def _(fname: str, pn: int = 1) -> None:
        punish = await perf_stat(func)(fname, pn)
        LOG().info(f"Checked pn={pn} time={perf_stat.last_time/1e3:.5f}s")
        return punish

    return _


ori_threads_runner = _default_threads_runner
threads_runner = _threads_runner_perf_stat(ori_threads_runner)


def set_threads_runner(enable_perf_log: bool = False) -> Callable[[TypeThreadsRunner], TypeThreadsRunner]:
    def _(new_runner: TypeThreadsRunner) -> TypeThreadsRunner:
        global ori_threads_runner, threads_runner
        ori_threads_runner = new_runner
        threads_runner = ori_threads_runner
        if enable_perf_log:
            threads_runner = _threads_runner_perf_stat(threads_runner)
        return ori_threads_runner

    return _

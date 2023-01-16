import asyncio
from typing import Awaitable, Callable

from aiotieba import LOG

from ... import executor
from ..._typing import Thread
from ...perf_stat import aperf_stat
from .. import post
from . import checker, filter, producer

TypeThreadRunner = Callable[[Thread], Awaitable[None]]


async def _default_thread_runner(thread: Thread) -> None:
    punish = await checker.checker(thread)
    if punish is not None:
        await executor.punish_executor(punish)

    punish = await post.runner.posts_runner(thread)
    if punish is not None:
        punish.obj = thread
        await executor.punish_executor(punish)


def _thread_runner_perf_stat(func: TypeThreadRunner) -> TypeThreadRunner:
    perf_stat = aperf_stat()

    async def _(thread: Thread) -> None:
        punish = await perf_stat(func)(thread)
        LOG().debug(f"Checked tid={thread.tid} time={perf_stat.last_time/1e3:.5f}s")
        return punish

    return _


ori_thread_runner = _default_thread_runner
thread_runner = _thread_runner_perf_stat(ori_thread_runner)


def set_thread_runner(enable_perf_log: bool = False) -> Callable[[TypeThreadRunner], TypeThreadRunner]:
    def _(new_runner: TypeThreadRunner) -> TypeThreadRunner:
        global ori_thread_runner, thread_runner
        ori_thread_runner = new_runner
        thread_runner = ori_thread_runner
        if enable_perf_log:
            thread_runner = _thread_runner_perf_stat(thread_runner)
        return ori_thread_runner

    return _


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
        await thread_runner(thread)


def _threads_runner_perf_stat(func: TypeThreadRunner) -> TypeThreadRunner:
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

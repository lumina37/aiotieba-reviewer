from typing import Awaitable, Callable

from aiotieba import LOG

from ... import executor
from ..._typing import Thread
from ...perf_stat import aperf_stat
from .. import posts
from . import checker

TypeThreadRunner = Callable[[Thread], Awaitable[None]]


async def _default_thread_runner(thread: Thread) -> None:
    punish = await checker.checker(thread)
    if punish is not None:
        await executor.punish_executor(punish)

    punish = await posts.runner.posts_runner(thread)
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

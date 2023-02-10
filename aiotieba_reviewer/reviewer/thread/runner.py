from typing import Awaitable, Callable

from aiotieba import LOG

from ... import executor
from ..._typing import Thread
from ...perf_stat import aperf_stat
from .. import posts
from . import checker

TypeThreadRunner = Callable[[Thread], Awaitable[None]]


async def __null_runner(_):
    pass


async def __default_runner(thread: Thread) -> None:
    punish = await checker.checker(thread)
    if punish is not None:
        await executor.punish_executor(punish)

    punish = await posts.runner.runner(thread)
    if punish is not None:
        punish.obj = thread
        await executor.punish_executor(punish)


def __runner_perf_stat(func: TypeThreadRunner) -> TypeThreadRunner:
    perf_stat = aperf_stat()

    async def _(thread: Thread) -> None:
        punish = await perf_stat(func)(thread)
        LOG().debug(f"Checked tid={thread.tid} time={perf_stat.last_time/1e3:.5f}s")
        return punish

    return _


ori_runner: TypeThreadRunner = __null_runner
runner: TypeThreadRunner = __null_runner


def __switch_runner() -> bool:
    global ori_runner, runner

    if ori_runner is __null_runner:
        ori_runner = __default_runner
        runner = __runner_perf_stat(ori_runner)
        return False

    else:
        return True


_set_runner_hook = None


def __hook():
    if __switch_runner():
        return
    _set_runner_hook()


# 下层checker被定义时应当通过__hook使能所有上层runner
checker._set_checker_hook = __hook
posts.runner._set_runner_hook = __hook


def set_thread_runner(enable_perf_log: bool = False) -> Callable[[TypeThreadRunner], TypeThreadRunner]:
    def _(new_runner: TypeThreadRunner) -> TypeThreadRunner:
        _set_runner_hook()

        global ori_runner, runner
        ori_runner = new_runner
        runner = ori_runner

        if enable_perf_log:
            runner = __runner_perf_stat(runner)

        return ori_runner

    return _

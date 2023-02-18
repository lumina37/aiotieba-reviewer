import asyncio
from typing import Awaitable, Callable

from aiotieba import LOG

from ... import executor
from ...perf_stat import aperf_stat
from ..thread import runner as t_runner
from . import filter, producer

TypeThreadsRunner = Callable[[str, int], Awaitable[None]]


async def __null_runner(_):
    pass


async def __default_runner(fname: str, pn: int = 1) -> None:
    threads = await producer.producer(fname, pn)

    for filt in filter._filters:
        punishes = await filt(threads)
        if punishes is None:
            continue
        for punish in punishes:
            if punish:
                threads.remove(punish.obj)
        await asyncio.gather(*[executor.punish_executor(p) for p in punishes])

    await asyncio.gather(*[t_runner.runner(t) for t in threads])


def __runner_perf_stat(func: TypeThreadsRunner) -> TypeThreadsRunner:
    perf_stat = aperf_stat()

    async def _(fname: str, pn: int = 1) -> None:
        punish = await perf_stat(func)(fname, pn)
        LOG().info(f"Checked pn={pn} time={perf_stat.last_time/1e3:.5f}s")
        return punish

    return _


ori_runner = __null_runner
runner = __null_runner


def __switch_runner() -> bool:
    global ori_runner, runner

    if ori_runner is __null_runner:
        ori_runner = __default_runner
        runner = __runner_perf_stat(ori_runner)
        return False

    else:
        return True


def __hook():
    if __switch_runner():
        return


# 下层checker被定义时应当通过__hook使能所有上层runner
filter._append_filter_hook = __hook
t_runner._set_runner_hook = __hook


def set_threads_runner(enable_perf_log: bool = False) -> Callable[[TypeThreadsRunner], TypeThreadsRunner]:
    def _(new_runner: TypeThreadsRunner) -> TypeThreadsRunner:
        global ori_runner, runner
        ori_runner = new_runner
        runner = ori_runner

        if enable_perf_log:
            runner = __runner_perf_stat(runner)

        return ori_runner

    return _

import asyncio
import contextlib
from typing import Generator, NoReturn

from .. import client, executor
from . import thread


async def run(time_interval: float = 0.0) -> NoReturn:
    """
    在第一页上循环运行审查

    Args:
        time_interval (float, optional): 每两次审查的时间间隔 以秒为单位. Defaults to 0.0.
    """

    while 1:
        await thread.runner._threads_runner(client._fname)
        await asyncio.sleep(time_interval)


async def run_multi_pn(time_interval: float = 0.0, pn_gen: Generator[int, None, None] = range(64, 0, -1)) -> None:
    """
    在多个页码上运行审查

    Args:
        time_interval (float, optional): 每两次审查的时间间隔 以秒为单位. Defaults to 0.0.
        pn_gen (Generator[int, None, None], optional): 页码生成器. Defaults to range(64, 0, -1).
    """

    if time_interval > 0:
        for pn in pn_gen:
            await thread.runner._threads_runner(client._fname, pn)
            await asyncio.sleep(time_interval)

    else:
        for pn in pn_gen:
            await thread.runner._threads_runner(client._fname, pn)


async def run_with_dyn_interval(dyn_interval: Generator[float, None, None]) -> None:
    """
    _summary_

    Args:
        dyn_interval (Generator[float, None, None]): 动态时间间隔生成器 以秒为单位 每进行一次审查循环迭代一次
    """

    for time_interval in dyn_interval:
        await thread.runner._threads_runner(client._fname)
        if time_interval:
            await asyncio.sleep(time_interval)


@contextlib.contextmanager
def no_test() -> None:
    """
    取消测试模式以实际执行删封
    """

    executor._punish_executor = executor.punish_executor
    yield
    executor._punish_executor = executor.punish_executor_test

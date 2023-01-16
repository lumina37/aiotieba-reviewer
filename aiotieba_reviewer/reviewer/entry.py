import asyncio
import contextlib
from typing import Generator, NoReturn

from .. import client, executor
from . import comment, post, thread


async def run(time_interval: float = 0.0) -> NoReturn:
    """
    在第一页上循环运行审查

    Args:
        time_interval (float, optional): 每两次审查的时间间隔 以秒为单位. Defaults to 0.0.
    """

    while 1:
        await thread.runner.threads_runner(client._fname)
        await asyncio.sleep(time_interval)


async def run_with_dyn_interval(dyn_interval: Generator[float, None, None]) -> None:
    """
    在第一页上循环运行审查 使用动态时间间隔

    Args:
        dyn_interval (Generator[float, None, None]): 动态时间间隔生成器 以秒为单位 每进行一次审查循环迭代一次
    """

    for time_interval in dyn_interval:
        await thread.runner.threads_runner(client._fname)
        if time_interval:
            await asyncio.sleep(time_interval)


async def run_multi_pn(pn_gen: Generator[int, None, None] = range(64, 0, -1)) -> None:
    """
    清洗多个页码 将禁用历史状态缓存以允许重复检查

    Args:
        pn_gen (Generator[int, None, None], optional): 页码生成器. Defaults to range(64, 0, -1).
    """

    thread.set_checker(True, False)(thread.checker.ori_checker)
    post.set_checker(True, False)(post.checker.ori_checker)
    comment.set_checker(True, False)(comment.checker.ori_checker)

    thread.runner.set_thread_runner(True)(thread.runner.ori_thread_runner)
    thread.runner.set_threads_runner(True)(thread.runner.ori_threads_runner)

    for pn in pn_gen:
        await thread.runner.threads_runner(client._fname, pn)


@contextlib.contextmanager
def no_test() -> None:
    """
    取消测试模式以实际执行删封
    """

    executor.punish_executor = executor.default_punish_executor
    thread.runner.set_thread_runner(False)(thread.runner.ori_thread_runner)
    thread.runner.set_threads_runner(False)(thread.runner.ori_threads_runner)
    yield
    executor.punish_executor = executor.default_punish_executor_test
    thread.runner.set_thread_runner(True)(thread.runner.ori_thread_runner)
    thread.runner.set_threads_runner(True)(thread.runner.ori_threads_runner)

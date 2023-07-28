import asyncio
import contextlib
from typing import Generator, List, NoReturn, Optional

from aiotieba.enums import PostSortType
from aiotieba.logging import get_logger as LOG

from .. import client, executor
from ..client import get_client
from ..punish import Punish
from ..typing import Post, Thread
from . import comment, post, posts, thread, threads


async def run(time_interval: float = 0.0) -> NoReturn:
    """
    在第一页上循环运行审查

    Args:
        time_interval (float, optional): 每两次审查的时间间隔 以秒为单位. Defaults to 0.0.
    """

    while 1:
        await threads.runner.runner(client._fname)
        await asyncio.sleep(time_interval)


async def run_with_dyn_interval(dyn_interval: Generator[float, None, None]) -> None:
    """
    在第一页上循环运行审查 使用动态时间间隔

    Args:
        dyn_interval (Generator[float, None, None]): 动态时间间隔生成器 以秒为单位 每进行一次审查循环迭代一次
    """

    for time_interval in dyn_interval:
        await threads.runner.runner(client._fname)
        if time_interval:
            await asyncio.sleep(time_interval)


async def run_multi_pn(pn_gen: Generator[int, None, None] = range(4, 0, -1)) -> None:
    """
    清洗多个页码 将禁用历史状态缓存以允许重复检查

    Args:
        pn_gen (Generator[int, None, None], optional): 页码生成器. Defaults to range(64, 0, -1).
    """

    thread.runner.set_thread_runner(True)(thread.runner.ori_runner)
    threads.runner.set_threads_runner(True)(threads.runner.ori_runner)

    thread.set_checker(True, False)(thread.checker.ori_checker)
    post.set_checker(True, False)(post.checker.ori_checker)
    comment.set_checker(True, False)(comment.checker.ori_checker)

    for pn in pn_gen:
        await threads.runner.runner(client._fname, pn)


async def run_multi_pn_with_time_threshold(
    time_threshold: int, pn_gen: Generator[int, None, None] = range(4, 0, -1)
) -> None:
    """
    清洗多个页码中的较新内容 将禁用历史状态缓存以允许重复检查

    Args:
        time_threshold (int): 创建时间晚于该值的内容都会被检查. 10位时间戳 以秒为单位.
        pn_gen (Generator[int, None, None], optional): 页码生成器. Defaults to range(4, 0, -1).
    """

    thread.runner.set_thread_runner(True)(thread.runner.ori_runner)
    threads.runner.set_threads_runner(True)(threads.runner.ori_runner)

    thread.set_checker(True, False)(thread.checker.ori_checker)
    post.set_checker(True, False)(post.checker.ori_checker)
    comment.set_checker(True, False)(comment.checker.ori_checker)

    _client = await get_client()

    @posts.set_producer
    async def _(thread: Thread) -> List[Post]:
        post_list = []

        last_posts = await _client.get_posts(
            thread.tid, pn=0xFFFF, sort=PostSortType.DESC, with_comments=True, comment_rn=10
        )
        end_idx = len(last_posts)
        for i, p in enumerate(last_posts):
            if p.create_time < time_threshold:
                end_idx = i
        post_list += last_posts._objs[:end_idx]

        for pn in range(last_posts.page.total_page - 1, 0, -1):
            _posts = await _client.get_posts(
                thread.tid, pn=pn, sort=PostSortType.DESC, with_comments=True, comment_rn=10
            )
            end_idx = len(_posts)
            for i, p in enumerate(_posts):
                if p.create_time < time_threshold:
                    end_idx = i
            post_list += _posts._objs[:end_idx]
            if end_idx != len(_posts):
                break

        return post_list

    for pn in pn_gen:
        await threads.runner.runner(client._fname, pn)


async def test(tid: int, pid: int = 0, is_comment: bool = False) -> Optional[Punish]:
    client = await get_client()
    if not pid:
        posts = await client.get_posts(tid, rn=0)
        thread.checker.set_checker(True, False)(thread.checker.ori_checker)
        return await thread.checker.checker(posts.thread)
    else:
        if not is_comment:
            comments = await client.get_comments(tid, pid, is_comment=False)
            post.checker.set_checker(True, False)(post.checker.ori_checker)
            return await post.checker.checker(comments.post)
        else:
            comments = await client.get_comments(tid, pid, is_comment=True)
            for _comment in comments:
                if _comment.pid == pid:
                    comment.checker.set_checker(True, False)(comment.checker.ori_checker)
                    return await comment.checker.checker(_comment)
            LOG().warning("Comment not exist")


@contextlib.asynccontextmanager
async def no_test() -> None:
    """
    取消测试模式以实际执行删封
    """

    thread.runner.set_thread_runner(False)(thread.runner.ori_runner)
    threads.runner.set_threads_runner(False)(threads.runner.ori_runner)

    try:
        executor.punish_executor = executor.default_punish_executor
        yield

    except Exception:
        import traceback

        LOG().critical(traceback.format_exc())

    executor.punish_executor = executor.default_punish_executor_test
    thread.runner.set_thread_runner(True)(thread.runner.ori_runner)
    threads.runner.set_threads_runner(True)(threads.runner.ori_runner)

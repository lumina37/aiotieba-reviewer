from typing import Awaitable, Callable, Optional

from ... import client
from ..._typing import Thread
from ...punish import Punish
from ..user_checker import user_checker

TypeThreadChecker = Callable[[Thread], Awaitable[Optional[Punish]]]


def thread_id_checker(func):
    """
    装饰器: 使用历史状态缓存避免重复检查
    """

    async def _(thread: Thread) -> Optional[Punish]:

        prev_last_time = client._db_sqlite.get_id(thread.tid)
        if prev_last_time is not None:
            if thread.last_time == prev_last_time:
                return
            if thread.last_time < prev_last_time:
                client._db_sqlite.add_id(thread.tid, tag=thread.last_time)
                return

        punish = await func(thread)
        if punish:
            return punish

        client._db_sqlite.add_id(thread.tid, tag=thread.last_time)

    return _


def set_thread_user_level(func):
    """
    装饰器: 填补发帖用户等级
    """

    async def _(thread: Thread) -> Optional[Punish]:
        _client = await client.get_client()
        posts = await _client.get_posts(thread.tid, rn=0)
        thread._user = posts.thread.user
        return await func(thread)

    return _


async def _default_checker(thread: Thread) -> Optional[Punish]:
    pass


ori_checker = _default_checker
checker = user_checker(ori_checker)


def set_checker(
    enable_user_checker: bool = True, enable_id_checker: bool = False
) -> Callable[[TypeThreadChecker], TypeThreadChecker]:
    """
    装饰器: 设置主题帖检查函数

    Args:
        enable_user_checker (bool, optional): 是否检查发帖用户的黑白名单状态. Defaults to True.
        enable_id_checker (bool, optional): 是否使用历史状态缓存避免重复检查. Defaults to False.

    Returns:
        Callable[[TypeThreadChecker], TypeThreadChecker]
    """

    def _(new_checker: TypeThreadChecker) -> TypeThreadChecker:
        global ori_checker, checker
        ori_checker = new_checker
        checker = ori_checker
        checker = set_thread_user_level(checker)
        if enable_user_checker:
            checker = user_checker(checker)
        if enable_id_checker:
            checker = thread_id_checker(checker)
        return ori_checker

    return _

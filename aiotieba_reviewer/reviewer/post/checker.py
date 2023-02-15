from typing import Awaitable, Callable, Optional

from ... import client
from ..._typing import Post
from ...punish import Punish
from ..user_checker import _user_checker

TypePostChecker = Callable[[Post], Awaitable[Optional[Punish]]]


def __id_checker(func):
    """
    装饰器: 使用历史状态缓存避免重复检查
    """

    async def _(post: Post) -> Optional[Punish]:
        prev_reply_num = client._db_sqlite.get_id(post.pid)
        if prev_reply_num is not None:
            if post.reply_num == prev_reply_num:
                return
            elif post.reply_num < prev_reply_num:
                client._db_sqlite.add_id(post.pid, tag=post.reply_num)
                return

        punish = await func(post)
        if punish:
            return punish

        client._db_sqlite.add_id(post.pid, tag=post.reply_num)

    return _


async def __default_checker(_):
    pass


ori_checker: TypePostChecker = __default_checker
checker: TypePostChecker = _user_checker(ori_checker)


_set_checker_hook = None


def set_checker(
    enable_user_checker: bool = True, enable_id_checker: bool = True
) -> Callable[[TypePostChecker], TypePostChecker]:
    """
    装饰器: 设置回复检查函数

    Args:
        enable_user_checker (bool, optional): 是否检查发帖用户的黑白名单状态. Defaults to True.
        enable_id_checker (bool, optional): 是否使用历史状态缓存避免重复检查. Defaults to True.

    Returns:
        Callable[[TypePostChecker], TypePostChecker]
    """

    def _(new_checker: TypePostChecker) -> TypePostChecker:
        if new_checker is __default_checker:
            return new_checker

        _set_checker_hook()

        global ori_checker, checker
        ori_checker = new_checker
        checker = ori_checker

        if enable_user_checker:
            checker = _user_checker(checker)
        if enable_id_checker:
            checker = __id_checker(checker)

        return ori_checker

    return _

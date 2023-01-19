from typing import Awaitable, Callable, Optional

from ... import client
from ..._typing import Comment
from ...punish import Punish
from ..user_checker import user_checker

TypeCommentChecker = Callable[[Comment], Awaitable[Optional[Punish]]]


def comment_id_checker(func):
    """
    装饰器: 使用历史状态缓存避免重复检查
    """

    async def _(comment: Comment) -> Optional[Punish]:

        if client._db_sqlite.get_id(comment.pid) != -1:
            return

        punish = await func(comment)
        if punish:
            return punish

        client._db_sqlite.add_id(comment.pid)

    return _


async def _default_comment_checker(comment: Comment) -> Optional[Punish]:
    pass


ori_checker = _default_comment_checker
checker = user_checker(ori_checker)


def set_checker(
    enable_user_checker: bool = True, enable_id_checker: bool = True
) -> Callable[[TypeCommentChecker], TypeCommentChecker]:
    """
    装饰器: 设置楼中楼检查函数

    Args:
        enable_user_checker (bool, optional): 是否检查发帖用户的黑白名单状态. Defaults to True.
        enable_id_checker (bool, optional): 是否使用历史状态缓存避免重复检查. Defaults to True.

    Returns:
        Callable[[TypeCommentChecker], TypeCommentChecker]
    """

    def _(new_checker: TypeCommentChecker) -> TypeCommentChecker:
        global ori_checker, checker
        ori_checker = new_checker
        checker = ori_checker
        if enable_user_checker:
            checker = user_checker(checker)
        if enable_id_checker:
            checker = comment_id_checker(checker)
        return ori_checker

    return _

from typing import Awaitable, Callable, Optional

from ... import executor
from ..._typing import Comment
from ...punish import Punish
from . import checker

TypeCommentRunner = Callable[[Comment], Awaitable[Optional[Punish]]]


async def _default_comment_runner(comment: Comment) -> Optional[Punish]:
    punish = await checker.checker(comment)
    if punish is not None:
        punish = await executor.punish_executor(punish)
        if punish is not None:
            return punish


comment_runner = _default_comment_runner


def set_comment_runner(new_runner: TypeCommentRunner) -> TypeCommentRunner:
    global comment_runner
    comment_runner = new_runner
    return new_runner

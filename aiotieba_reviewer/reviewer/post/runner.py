from typing import Awaitable, Callable, Optional

from ... import executor
from ..._typing import Post
from ...punish import Punish
from .. import comments
from . import checker

TypePostRunner = Callable[[Post], Awaitable[Optional[Punish]]]


async def default_runner(post: Post) -> Optional[Punish]:
    punish = await checker.checker(post)
    if punish is not None:
        punish = await executor.punish_executor(punish)
        if punish is not None:
            return punish

    punish = await comments.runner.comments_runner(post)
    if punish is not None:
        punish.obj = post
        return punish


post_runner = default_runner


def set_post_runner(new_runner: TypePostRunner) -> TypePostRunner:
    global post_runner
    post_runner = new_runner
    return new_runner

from typing import Awaitable, Callable, Optional

from ... import executor
from ..._typing import Comment
from ...punish import Punish
from . import checker

TypeCommentRunner = Callable[[Comment], Awaitable[Optional[Punish]]]


async def __null_runner(_):
    pass


async def __default_runner(comment: Comment) -> Optional[Punish]:
    punish = await checker.checker(comment)
    if punish is not None:
        punish = await executor.punish_executor(punish)
        if punish is not None:
            return punish


runner: TypeCommentRunner = __null_runner


def __switch_runner() -> bool:
    global runner

    if runner is __null_runner:
        runner = __default_runner
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


def set_comment_runner(new_runner: TypeCommentRunner) -> TypeCommentRunner:
    _set_runner_hook()

    global runner
    runner = new_runner

    return new_runner

from collections.abc import Awaitable, Callable

from ... import executor
from ...punish import Punish
from ...typing import Post
from .. import comments
from . import checker

TypePostRunner = Callable[[Post], Awaitable[Punish | None]]


async def __null_runner(_):
    pass


async def __default_runner(post: Post) -> Punish | None:
    punish = await checker.checker(post)
    if punish is not None:
        punish = await executor.punish_executor(punish)
        if punish is not None:
            return punish

    punish = await comments.runner.runner(post)
    if punish is not None:
        punish.obj = post
        punish = await executor.punish_executor(punish)
        if punish is not None:
            return punish


runner: TypePostRunner = __null_runner


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
comments.runner._set_runner_hook = __hook


def set_post_runner(new_runner: TypePostRunner) -> TypePostRunner:
    _set_runner_hook()

    global runner
    runner = new_runner

    return new_runner

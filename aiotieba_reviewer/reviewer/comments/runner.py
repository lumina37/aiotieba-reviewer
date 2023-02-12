import asyncio
from typing import Awaitable, Callable, Optional

from ... import executor
from ..._typing import Post
from ...punish import Punish
from ..comment import runner as c_runner
from . import filter, producer

TypeCommentsRunner = Callable[[Post], Awaitable[Optional[Punish]]]


async def __null_runner(_):
    pass


async def __default_runner(post: Post) -> Optional[Punish]:
    comments = await producer.producer(post)

    for filt in filter._filters:
        punishes = await filt(comments)
        if punishes is None:
            continue
        for punish in punishes:
            if punish:
                comments.remove(punish.obj)
        punishes = await asyncio.gather(*[executor.punish_executor(p) for p in punishes])
        if punishes:
            punish = Punish(post)
            for _punish in punishes:
                if _punish is not None:
                    punish |= _punish
            return punish

    punishes = await asyncio.gather(*[c_runner.runner(c) for c in comments])
    if punishes:
        punish = Punish(post)
        for _punish in punishes:
            if _punish is not None:
                punish |= _punish
        return punish


runner: TypeCommentsRunner = __null_runner


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
filter._append_filter_hook = __hook
c_runner._set_runner_hook = __hook


def set_comments_runner(new_runner: TypeCommentsRunner) -> TypeCommentsRunner:
    _set_runner_hook()

    global runner
    runner = new_runner

    return new_runner

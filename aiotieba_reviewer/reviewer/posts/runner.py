import asyncio
from typing import Awaitable, Callable, Optional

from ... import executor
from ..._typing import Thread
from ...punish import Punish
from ..post import runner as p_runner
from . import filter, producer

TypePostsRunner = Callable[[Thread], Awaitable[Optional[Punish]]]


async def __null_runner(_):
    pass


async def __default_runner(thread: Thread) -> Optional[Punish]:
    posts = await producer.producer(thread)

    for filt in filter._filters:
        punishes = await filt(posts)
        if punishes is None:
            continue
        for punish in punishes:
            if punish:
                posts.remove(punish.obj)
        punishes = await asyncio.gather(*[executor.punish_executor(p) for p in punishes])
        if punishes:
            punish = Punish(thread)
            for _punish in punishes:
                if _punish is not None:
                    punish |= _punish
            return punish

    punishes = await asyncio.gather(*[p_runner.runner(p) for p in posts])
    punishes = [p for p in punishes if p is not None]
    if punishes:
        punish = Punish(thread)
        for _punish in punishes:
            if _punish is not None:
                punish |= _punish
        return punish


runner: TypePostsRunner = __null_runner


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
p_runner._set_runner_hook = __hook


def set_posts_runner(new_runner: TypePostsRunner) -> TypePostsRunner:
    _set_runner_hook()

    global runner
    runner = new_runner

    return new_runner

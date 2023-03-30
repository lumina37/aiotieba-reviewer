import asyncio
import itertools
from typing import Awaitable, Callable, Optional

from ... import executor
from ...punish import Punish
from ...typing import Thread
from ..post import runner as p_runner
from . import filter, producer

TypePostsRunner = Callable[[Thread], Awaitable[Optional[Punish]]]


async def __null_runner(_):
    pass


async def __default_runner(thread: Thread) -> Optional[Punish]:
    posts = await producer.producer(thread)

    rethrow_punish = None

    for filt in filter._filters:
        punishes = await filt(posts)
        if punishes is None:
            continue
        for punish in punishes:
            if punish:
                posts.remove(punish.obj)
                _p = await executor.punish_executor(punish)
                if _p is not None:
                    if rethrow_punish is None:
                        rethrow_punish = Punish(thread)
                    rethrow_punish |= _p

    for i in itertools.count():
        _posts = posts[i * 50 : (i + 1) * 50]
        if not _posts:
            break
        punishes = await asyncio.gather(*[p_runner.runner(p) for p in _posts])
        for _p in punishes:
            if _p is not None:
                if rethrow_punish is None:
                    rethrow_punish = Punish(thread)
                rethrow_punish |= _p

    return rethrow_punish


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

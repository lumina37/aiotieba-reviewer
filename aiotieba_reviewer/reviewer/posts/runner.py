import asyncio
from typing import Awaitable, Callable, Optional

from ... import executor
from ..._typing import Thread
from ...punish import Punish
from ..post import runner
from . import filter, producer

TypePostsRunner = Callable[[Thread], Awaitable[Optional[Punish]]]


async def _default_posts_runner(thread: Thread) -> Optional[Punish]:
    posts = await producer.producer(thread)

    for _filter in filter.filters:
        _posts = await _filter(posts)
        if _posts is not None:
            posts = _posts

    for filt in filter.filters:
        punishes = await filt(posts)
        if punishes is None:
            continue
        for punish in punishes:
            posts.remove(punish.obj)
        punishes = await asyncio.gather(*[executor.punish_executor(p) for p in punishes])
        if punishes:
            punish = Punish(thread)
            for _punish in punishes:
                if _punish is not None:
                    punish |= _punish
            return punish

    punishes = await asyncio.gather(*[runner.post_runner(p) for p in posts])
    punishes = [p for p in punishes if p is not None]
    if punishes:
        punish = Punish(thread)
        for _punish in punishes:
            if _punish is not None:
                punish |= _punish
        return punish


posts_runner = _default_posts_runner


def set_posts_runner(new_runner: TypePostsRunner) -> TypePostsRunner:
    global posts_runner
    posts_runner = new_runner
    return new_runner

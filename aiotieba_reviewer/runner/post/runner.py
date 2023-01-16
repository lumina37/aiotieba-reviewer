import asyncio
from typing import Awaitable, Callable, Optional

from ... import executor
from ..._misc import Punish
from ..._typing import Post, Thread
from .. import comment
from . import checker, filter, producer

TypePostRunner = Callable[[Post], Awaitable[Optional[Punish]]]


async def post_runner(post: Post) -> Optional[Punish]:
    punish = await checker._checker(post)
    if punish is not None:
        punish = await executor._punish_executor(punish)
        if punish is not None:
            return punish

    punish = await comment.runner._comments_runner(post)
    if punish is not None:
        punish.obj = post
        return punish


_post_runner = post_runner


def set_post_runner(runner: TypePostRunner) -> TypePostRunner:
    global _post_runner
    _post_runner = runner
    return runner


TypePostsRunner = Callable[[Thread], Awaitable[Optional[Punish]]]


async def posts_runner(thread: Thread) -> Optional[Punish]:
    posts = await producer._producer(thread)

    for _filter in filter._filters:
        _posts = await _filter(posts)
        if _posts is not None:
            posts = _posts

    punishes = asyncio.gather(*[post_runner(p) for p in posts])
    punishes = [p for p in punishes if p is not None]
    if punishes:
        punish = Punish(thread)
        for _punish in punishes:
            if _punish is not None:
                punish |= _punish
        return punish


_posts_runner = posts_runner


def set_posts_runner(runner: TypePostsRunner) -> TypePostsRunner:
    global _posts_runner
    _posts_runner = runner
    return runner

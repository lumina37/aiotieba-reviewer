import asyncio
from typing import Awaitable, Callable, Optional

from ... import executor
from ..._typing import Post, Thread
from ...classdef import Punish
from .. import comment
from . import checker, filter, producer

TypePostRunner = Callable[[Post], Awaitable[Optional[Punish]]]


async def _default_post_runner(post: Post) -> Optional[Punish]:
    punish = await checker.checker(post)
    if punish is not None:
        punish = await executor.punish_executor(punish)
        if punish is not None:
            return punish

    punish = await comment.runner.comments_runner(post)
    if punish is not None:
        punish.obj = post
        return punish


post_runner = _default_post_runner


def set_post_runner(new_runner: TypePostRunner) -> TypePostRunner:
    global post_runner
    post_runner = new_runner
    return new_runner


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

    punishes = await asyncio.gather(*[post_runner(p) for p in posts])
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

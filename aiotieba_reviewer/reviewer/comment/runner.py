import asyncio
from typing import Awaitable, Callable, Optional

from ... import executor
from ..._typing import Comment, Post
from ...classdef import Punish
from . import checker, filter, producer

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


TypeCommentsRunner = Callable[[Post], Awaitable[Optional[Punish]]]


async def _default_comments_runner(post: Post) -> Optional[Punish]:
    comments = await producer.producer(post)

    for filt in filter.filters:
        punishes = await filt(comments)
        if punishes is None:
            continue
        for punish in punishes:
            comments.remove(punish.obj)
        punishes = await asyncio.gather(*[executor.punish_executor(p) for p in punishes])
        if punishes:
            punish = Punish(post)
            for _punish in punishes:
                if _punish is not None:
                    punish |= _punish
            return punish

    punishes = await asyncio.gather(*[comment_runner(c) for c in comments])
    if punishes:
        punish = Punish(post)
        for _punish in punishes:
            if _punish is not None:
                punish |= _punish
        return punish


comments_runner = _default_comments_runner


def set_comments_runner(new_runner: TypeCommentsRunner) -> TypeCommentsRunner:
    global comments_runner
    comments_runner = new_runner
    return new_runner

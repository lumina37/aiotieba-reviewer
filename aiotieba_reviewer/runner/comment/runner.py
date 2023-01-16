import asyncio
from typing import Awaitable, Callable, Optional

from ... import executor
from ..._misc import Punish
from ..._typing import Comment, Post
from . import checker, filter, producer

TypeCommentRunner = Callable[[Comment], Awaitable[Optional[Punish]]]


async def comment_runner(comment: Comment) -> Optional[Punish]:
    punish = await checker._checker(comment)
    if punish is not None:
        punish = await executor._punish_executor(punish)
        if punish is not None:
            return punish


TypeCommentsRunner = Callable[[Post], Awaitable[Optional[Punish]]]


async def comments_runner(post: Post) -> Optional[Punish]:
    comments = await producer._producer(post)

    for _filter in filter._filters:
        _comments = await _filter(comments)
        if _comments is not None:
            comments = _comments

    punishes = await asyncio.gather(*[comment_runner(c) for c in comments])
    if punishes:
        punish = Punish(post)
        for _punish in punishes:
            if _punish is not None:
                punish |= _punish
        return punish


_comments_runner = comments_runner


def set_comments_runner(runner: TypeCommentsRunner) -> TypeCommentsRunner:
    global _comments_runner
    _comments_runner = runner
    return runner

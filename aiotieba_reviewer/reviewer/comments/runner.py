import asyncio
from typing import Awaitable, Callable, Optional

from ... import executor
from ..._typing import Post
from ...punish import Punish
from ..comment import runner
from . import filter, producer

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

    punishes = await asyncio.gather(*[runner.comment_runner(c) for c in comments])
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

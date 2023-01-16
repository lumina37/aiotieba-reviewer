from typing import Awaitable, Callable, List

from ..._typing import Post, Thread
from ...client import get_client

TypePostsProducer = Callable[[Thread], Awaitable[List[Post]]]


async def _posts_producer(thread: Thread) -> List[Post]:

    client = await get_client()

    if thread.reply_num > 30:
        last_rn = _last_rn if (_last_rn := thread.reply_num - 30) <= 30 else 30
        last_posts = await client.get_posts(
            thread.tid, pn=0xFFFF, rn=last_rn, sort=1, with_comments=True, comment_rn=30
        )
        post_set = set(last_posts._objs)
        first_posts = await client.get_posts(thread.tid, with_comments=True, comment_rn=4)
        post_set.update(first_posts._objs)
        post_list = list(post_set)

    else:
        posts = await client.get_posts(thread.tid, with_comments=True, comment_rn=10)
        post_list = posts._objs

    return post_list


_producer = _posts_producer


def set_posts_producer(producer: TypePostsProducer) -> TypePostsProducer:
    global _producer
    _producer = producer
    return producer

from typing import Awaitable, Callable, List

from ..._typing import Comment, Post
from ...client import get_client

TypeCommentsProducer = Callable[[Post], Awaitable[List[Comment]]]


async def __default_producer(post: Post) -> List[Comment]:
    client = await get_client()

    reply_num = post.reply_num
    if reply_num > 10 or (len(post.comments) != reply_num and reply_num <= 10):
        last_comments = await client.get_comments(post.tid, post.pid, pn=post.reply_num // 30 + 1)
        comment_set = set(post.comments)
        comment_set.update(last_comments._objs)
        comment_list = list(comment_set)

    else:
        comment_list = post.comments

    return comment_list


producer: TypeCommentsProducer = __default_producer


def set_producer(new_producer: TypeCommentsProducer) -> TypeCommentsProducer:
    global producer
    producer = new_producer
    return new_producer

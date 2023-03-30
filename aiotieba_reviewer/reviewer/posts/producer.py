from typing import Awaitable, Callable, List

from aiotieba.enums import PostSortType

from ...client import get_client
from ...typing import Post, Thread

TypePostsProducer = Callable[[Thread], Awaitable[List[Post]]]


async def __default_producer(thread: Thread) -> List[Post]:
    client = await get_client()

    last_posts = await client.get_posts(
        thread.tid,
        pn=0xFFFF,
        sort=PostSortType.DESC,
        with_comments=True,
        comment_rn=10,
    )

    if last_posts and last_posts[-1].floor != 1:
        last_floor = last_posts[0].floor
        need_rn = last_floor - len(last_posts)
        if need_rn > 0:
            post_set = set(last_posts._objs)
            if need_rn <= 30:
                first_posts = await client.get_posts(thread.tid, rn=need_rn, with_comments=True, comment_rn=10)
                post_set.update(first_posts._objs)
            else:
                first_posts = await client.get_posts(thread.tid, rn=need_rn, with_comments=True, comment_rn=10)
                post_set.update(first_posts._objs)
                hot_posts = await client.get_posts(thread.tid, sort=PostSortType.HOT, with_comments=True, comment_rn=10)
                post_set.update(hot_posts._objs)
            post_list = list(post_set)
        else:
            post_list = last_posts._objs
    else:
        post_list = last_posts._objs

    return post_list


producer = __default_producer


def set_producer(new_producer: TypePostsProducer) -> TypePostsProducer:
    global producer
    producer = new_producer
    return new_producer

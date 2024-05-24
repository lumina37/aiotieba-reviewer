from collections.abc import Awaitable, Callable

from ...client import get_client
from ...typing import Thread

TypeThreadsProducer = Callable[[], Awaitable[list[Thread]]]


async def __default_producer(fname: str, pn: int = 1) -> list[Thread]:
    client = await get_client()
    threads = await client.get_threads(fname, pn)
    thread_list = [t for t in threads if not t.is_livepost]
    return thread_list


producer = __default_producer


def set_producer(new_producer: TypeThreadsProducer) -> TypeThreadsProducer:
    global producer
    producer = new_producer
    return new_producer

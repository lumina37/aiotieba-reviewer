from typing import Awaitable, Callable, List

from ..._typing import Thread
from ...client import get_client

TypeThreadsProducer = Callable[[], Awaitable[List[Thread]]]


async def _default_threads_producer(fname: str, pn: int = 1) -> List[Thread]:
    client = await get_client()
    threads = await client.get_threads(fname, pn)
    thread_list = [t for t in threads if not t.is_livepost]
    return thread_list


producer = _default_threads_producer


def set_producer(new_producer: TypeThreadsProducer) -> TypeThreadsProducer:
    global producer
    producer = new_producer
    return new_producer

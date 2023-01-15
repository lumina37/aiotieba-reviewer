from typing import Awaitable, Callable, List, Optional

from ..._typing import Thread

TypeThreadsFilter = Callable[[List[Thread]], Awaitable[Optional[List[Thread]]]]

_filters = []


def set_threads_filters(filters: List[TypeThreadsFilter]) -> None:
    global _filters
    _filters = filters

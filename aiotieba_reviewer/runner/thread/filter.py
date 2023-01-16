from typing import Awaitable, Callable, List, Optional

from ..._typing import Thread

TypeThreadsFilter = Callable[[List[Thread]], Awaitable[Optional[List[Thread]]]]

_filters: List[TypeThreadsFilter] = []


def append_threads_filter(filter: TypeThreadsFilter) -> TypeThreadsFilter:
    _filters.append(filter)
    return filter

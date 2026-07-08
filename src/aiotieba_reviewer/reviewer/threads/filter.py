from collections.abc import Awaitable, Callable

from ...punish import Punish
from ...typing import Thread

TypeThreadsFilter = Callable[[list[Thread]], Awaitable[list[Punish] | None]]

_filters: list[TypeThreadsFilter] = []

_append_filter_hook = None


def append_filter(new_filter: TypeThreadsFilter) -> TypeThreadsFilter:
    _append_filter_hook()
    _filters.append(new_filter)
    return new_filter

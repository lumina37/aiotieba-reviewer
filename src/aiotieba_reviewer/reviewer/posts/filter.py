from collections.abc import Awaitable, Callable

from ...punish import Punish
from ...typing import Post

TypePostsFilter = Callable[[list[Post]], Awaitable[list[Punish] | None]]

_filters: list[TypePostsFilter] = []

_append_filter_hook = None


def append_filter(new_filter: TypePostsFilter) -> TypePostsFilter:
    _append_filter_hook()
    _filters.append(new_filter)
    return new_filter

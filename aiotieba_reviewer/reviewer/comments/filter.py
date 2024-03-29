from collections.abc import Awaitable, Callable

from ...punish import Punish
from ...typing import Comment

TypeCommentsFilter = Callable[[list[Comment]], Awaitable[list[Punish] | None]]

_filters: list[TypeCommentsFilter] = []

_append_filter_hook = None


def append_filter(new_filter: TypeCommentsFilter) -> TypeCommentsFilter:
    _append_filter_hook()
    _filters.append(new_filter)
    return new_filter

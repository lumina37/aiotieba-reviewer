from typing import Awaitable, Callable, List, Optional

from ..._typing import Post
from ...punish import Punish

TypePostsFilter = Callable[[List[Post]], Awaitable[Optional[List[Punish]]]]

_filters: List[TypePostsFilter] = []

_append_filter_hook = None


def append_filter(new_filter: TypePostsFilter) -> TypePostsFilter:
    _append_filter_hook()
    _filters.append(new_filter)
    return new_filter

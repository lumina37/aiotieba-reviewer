from typing import Awaitable, Callable, List, Optional

from ..._typing import Comment

TypeCommentsFilter = Callable[[List[Comment]], Awaitable[Optional[List[Comment]]]]

_filters: List[TypeCommentsFilter] = []


def append_comments_filter(filter: TypeCommentsFilter) -> TypeCommentsFilter:
    _filters.append(filter)
    return filter

from typing import Awaitable, Callable, List, Optional

from ..._typing import Comment

TypeCommentsFilter = Callable[[List[Comment]], Awaitable[Optional[List[Comment]]]]

filters: List[TypeCommentsFilter] = []


def append_filter(new_filter: TypeCommentsFilter) -> TypeCommentsFilter:
    filters.append(new_filter)
    return new_filter

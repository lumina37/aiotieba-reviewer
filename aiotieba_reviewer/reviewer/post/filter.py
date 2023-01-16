from typing import Awaitable, Callable, List, Optional

from ..._typing import Post

TypePostsFilter = Callable[[List[Post]], Awaitable[Optional[List[Post]]]]

filters: List[TypePostsFilter] = []


def append_filter(new_filter: TypePostsFilter) -> TypePostsFilter:
    filters.append(new_filter)
    return new_filter

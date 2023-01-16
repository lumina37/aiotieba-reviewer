from typing import Awaitable, Callable, List, Optional

from ..._typing import Post

TypePostsFilter = Callable[[List[Post]], Awaitable[Optional[List[Post]]]]

_filters: List[TypePostsFilter] = []


def append_posts_filter(filter: TypePostsFilter) -> TypePostsFilter:
    _filters.append(filter)
    return filter

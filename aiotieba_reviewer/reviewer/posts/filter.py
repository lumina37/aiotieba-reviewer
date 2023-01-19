from typing import Awaitable, Callable, List, Optional

from ..._typing import Post
from ...punish import Punish

TypePostsFilter = Callable[[List[Post]], Awaitable[Optional[List[Punish]]]]

filters: List[TypePostsFilter] = []


def append_filter(new_filter: TypePostsFilter) -> TypePostsFilter:
    filters.append(new_filter)
    return new_filter

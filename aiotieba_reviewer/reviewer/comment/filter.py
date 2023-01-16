from typing import Awaitable, Callable, List, Optional

from ..._typing import Comment
from ...classdef import Punish

TypeCommentsFilter = Callable[[List[Comment]], Awaitable[Optional[List[Punish]]]]

filters: List[TypeCommentsFilter] = []


def append_filter(new_filter: TypeCommentsFilter) -> None:
    filters.append(new_filter)

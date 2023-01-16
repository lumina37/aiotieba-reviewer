from typing import Awaitable, Callable, List, Optional

from ..._typing import Thread
from ...classdef import Punish

TypeThreadsFilter = Callable[[List[Thread]], Awaitable[Optional[List[Punish]]]]

filters: List[TypeThreadsFilter] = []


def append_filter(new_filter: TypeThreadsFilter) -> TypeThreadsFilter:
    filters.append(new_filter)
    return new_filter

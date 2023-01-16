from typing import Awaitable, Callable, Optional

from ..._misc import Punish
from ..._typing import Post

TypePostChecker = Callable[[Post], Awaitable[Optional[Punish]]]


async def _post_checker(post: Post) -> Optional[Punish]:
    pass


_checker = _post_checker


def set_post_checker(checker: TypePostChecker) -> TypePostChecker:
    global _checker
    _checker = checker
    return checker

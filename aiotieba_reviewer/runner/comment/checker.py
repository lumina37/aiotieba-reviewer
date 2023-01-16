from typing import Awaitable, Callable, Optional

from ..._misc import Punish
from ..._typing import Comment

TypeCommentChecker = Callable[[Comment], Awaitable[Optional[Punish]]]


async def _comment_checker(comment: Comment) -> Optional[Punish]:
    pass


_checker = _comment_checker


def set_comment_checker(checker: TypeCommentChecker) -> TypeCommentChecker:
    global _checker
    _checker = checker
    return checker

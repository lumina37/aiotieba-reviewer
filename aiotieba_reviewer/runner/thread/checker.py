from typing import Awaitable, Callable, Optional

from ..._misc import Punish
from ..._typing import Thread

TypeThreadChecker = Callable[[Thread], Awaitable[Optional[Punish]]]


async def _thread_checker(thread: Thread) -> Optional[Punish]:
    pass


_checker = _thread_checker


def set_thread_checker(checker: TypeThreadChecker) -> TypeThreadChecker:
    global _checker
    _checker = checker
    return checker

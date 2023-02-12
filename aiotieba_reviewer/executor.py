import asyncio
from typing import Awaitable, Callable, Optional, Protocol

from aiotieba import LOG

from .client import get_client, get_fname
from .enums import Ops
from .punish import Punish


class TypeDeleteList(Protocol):
    async def append(self, pid: int) -> None:
        pass


class DeleteList(object):
    """
    待删除pid的列表

    execute_timeout (float): 插入元素后，若发现没有计划中的删除任务
        则在execute_timeout秒后执行一次删除操作. Defaults to 10.0.
    maxlen (int): 列表长度达到该值时立刻触发一次删除. Defaults to 30.

    Note:
        如果在计划的删除任务实施前，因为列表长度超限而触发了一次删除
        那么计划的删除任务会被取消
    """

    __slots__ = [
        '_execute_timeout',
        '_maxlen',
        '_delete_task',
        '_pids',
    ]

    def __init__(self, execute_timeout: float = 10.0, maxlen=30) -> None:
        self._execute_timeout = execute_timeout
        self._maxlen = maxlen
        self._delete_task: asyncio.Task = None
        self._pids = []

    async def append(self, pid: int) -> None:
        """
        将一个pid推入待删除列表

        Args:
            pid (int)
        """

        self._pids.append(pid)

        if len(self._pids) == self._maxlen:
            if not self._delete_task.done():
                self._delete_task.cancel()
            await self._delete_all()
        else:
            if self._delete_task is None or self._delete_task.done():
                self._delete_task = asyncio.create_task(self._delete_all_after_sleep())

    async def _delete_all(self) -> None:
        client = await get_client()
        await client.del_posts(get_fname(), self._pids)
        self._pids.clear()

    async def _delete_all_after_sleep(self) -> None:
        try:
            await asyncio.sleep(self._execute_timeout)
            await self._delete_all()
        except asyncio.CancelledError:
            return


delete_list = DeleteList()


def set_delete_list(_delete_list: TypeDeleteList) -> None:
    """
    设置删除列表

    Args:
        delete_list (TypeDeleteList)
    """

    global delete_list
    delete_list = _delete_list


TypePunishExecutor = Callable[[Punish], Awaitable[Optional[Punish]]]


async def default_punish_executor(punish: Punish) -> Optional[Punish]:
    if day := punish.day:
        client = await get_client()
        await client.block(get_fname(), punish.obj.user.portrait, day=day, reason=punish.note)

    op = punish.op
    if op == Ops.NORMAL:
        return
    if op == Ops.DELETE:
        LOG().info(
            f"Del {punish.obj.__class__.__name__}. text={punish.obj.text} user={punish.obj.user!r} note={punish.note}"
        )
        await delete_list.append(punish.obj.pid)
        return
    if op == Ops.DEBUG:
        LOG().info(
            f"Debug {punish.obj.__class__.__name__}. obj={punish.obj} user={punish.obj.user!r} note={punish.note}"
        )
        return
    if op == Ops.HIDE:
        LOG().info(
            f"Hide {punish.obj.__class__.__name__}. text={punish.obj.text} user={punish.obj.user!r} note={punish.note}"
        )
        client = await get_client()
        await client.hide_thread(get_fname(), punish.obj.tid)
        return
    if op & Ops.PARENT == Ops.PARENT:
        op &= ~Ops.PARENT
        punish.op = op
        return punish
    if op & Ops.GRANDPARENT == Ops.GRANDPARENT:
        op &= ~Ops.GRANDPARENT
        op &= Ops.PARENT
        punish.op = op
        return punish


class _punish_executor_test(object):
    __slots__ = ['punishes']

    def __init__(self) -> None:
        self.punishes = []

    async def __call__(self, punish: Punish) -> Optional[Punish]:
        if day := punish.day:
            LOG().info(f"Block. user={punish.obj.user!r} day={day} note={punish.note}")

        op = punish.op
        if op == Ops.NORMAL:
            return
        if op == Ops.DELETE:
            LOG().info(
                f"Del {punish.obj.__class__.__name__}. text={punish.obj.text} user={punish.obj.user!r} note={punish.note}"
            )
            self.punishes.append(punish)
            return
        if op == Ops.DEBUG:
            LOG().info(
                f"Debug {punish.obj.__class__.__name__}. obj={punish.obj} user={punish.obj.user!r} note={punish.note}"
            )
            return
        if op == Ops.HIDE:
            LOG().info(
                f"Hide {punish.obj.__class__.__name__}. text={punish.obj.text} user={punish.obj.user!r} note={punish.note}"
            )
            self.punishes.append(punish)
            return
        if op & Ops.PARENT == Ops.PARENT:
            op &= ~Ops.PARENT
            return Punish(op, punish.day, punish.note)
        if op & Ops.GRANDPARENT == Ops.GRANDPARENT:
            op &= ~Ops.GRANDPARENT
            op &= Ops.PARENT
            return Punish(op, punish.day, punish.note)


default_punish_executor_test = _punish_executor_test()


punish_executor = default_punish_executor_test

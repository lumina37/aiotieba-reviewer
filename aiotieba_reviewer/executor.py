from typing import Awaitable, Callable, Optional

from aiotieba.logging import get_logger as LOG

from .client import get_client, get_fname
from .enums import Ops
from .punish import Punish

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
            f"Del {punish.obj.__class__.__name__}. tid={punish.obj.tid} pid={punish.obj.pid} text={punish.obj.text} user={punish.obj.user.log_name} note={punish.note}"
        )
        client = await get_client()
        await client.del_post(punish.obj.fid, punish.obj.tid, punish.obj.pid)
        return
    if op == Ops.PENDING:
        return punish
    if op == Ops.HIDE:
        LOG().info(
            f"Hide {punish.obj.__class__.__name__}. tid={punish.obj.tid} pid={punish.obj.pid} text={punish.obj.text} user={punish.obj.user.log_name} note={punish.note}"
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
        op |= Ops.PARENT
        punish.op = op
        return punish


async def default_punish_executor_test(punish: Punish) -> Optional[Punish]:
    if day := punish.day:
        client = await get_client()
        await client.block(get_fname(), punish.obj.user.portrait, day=day, reason=punish.note)

    op = punish.op
    if op == Ops.NORMAL:
        return
    if op == Ops.DELETE:
        LOG().info(
            f"Del {punish.obj.__class__.__name__}. tid={punish.obj.tid} pid={punish.obj.pid} text={punish.obj.text} user={punish.obj.user.log_name} note={punish.note}"
        )
        client = await get_client()
        return
    if op == Ops.PENDING:
        return punish
    if op == Ops.HIDE:
        LOG().info(
            f"Hide {punish.obj.__class__.__name__}. tid={punish.obj.tid} pid={punish.obj.pid} text={punish.obj.text} user={punish.obj.user.log_name} note={punish.note}"
        )
        client = await get_client()
        return
    if op & Ops.PARENT == Ops.PARENT:
        op &= ~Ops.PARENT
        punish.op = op
        return punish
    if op & Ops.GRANDPARENT == Ops.GRANDPARENT:
        op &= ~Ops.GRANDPARENT
        op |= Ops.PARENT
        punish.op = op
        return punish


punish_executor = default_punish_executor_test

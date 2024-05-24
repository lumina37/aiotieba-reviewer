import asyncio
from collections.abc import Awaitable, Callable

import aiotieba as tb
from aiotieba import get_logger as LOG

from .client import get_client, get_fname
from .enums import Ops
from .punish import Punish

TypePunishExecutor = Callable[[Punish], Awaitable[Punish | None]]


async def default_punish_executor(punish: Punish) -> Punish | None:
    if day := punish.day:
        client = await get_client()
        ret = await client.block(get_fname(), punish.obj.user.portrait, day=day, reason=punish.note)
        if isinstance(ret.err, tb.exception.TiebaServerError):
            if ret.err.code == 1211068:
                await client.unblock(get_fname(), punish.obj.user.user_id)
                await asyncio.sleep(1.5)
                await client.block(get_fname(), punish.obj.user.portrait, day=day, reason=punish.note)
            elif ret.err.code == 3150003:
                await client.block(get_fname(), punish.obj.user.portrait, day=10, reason=punish.note)

    op = punish.op
    if op == Ops.NORMAL:
        return
    if op == Ops.DELETE:
        LOG().info(f"Del {punish.obj}. note={punish.note}")
        op &= ~Ops.DELETE
        punish.op = op
        punish.day = 0
        client = await get_client()
        await client.del_post(punish.obj.fid, punish.obj.tid, punish.obj.pid)
        return punish
    if op == Ops.PENDING:
        return punish
    if op == Ops.HIDE:
        LOG().info(f"Hide {punish.obj}. note={punish.note}")
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


async def default_punish_executor_test(punish: Punish) -> Punish | None:
    if day := punish.day:
        LOG().info(f"Block. user={punish.obj.user!r} day={day} note={punish.note}")

    op = punish.op
    if op == Ops.NORMAL:
        return
    if op == Ops.DELETE:
        LOG().info(f"Del {punish.obj}. note={punish.note}")
        op &= ~Ops.DELETE
        punish.op = op
        punish.day = 0
        return punish
    if op == Ops.PENDING:
        return punish
    if op == Ops.HIDE:
        LOG().info(f"Hide {punish.obj}. note={punish.note}")
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

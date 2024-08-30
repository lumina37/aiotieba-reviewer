from __future__ import annotations

import abc
import asyncio
import dataclasses as dcs
import functools
import itertools
import re
import time
from collections.abc import Callable
from typing import Protocol

import aiotieba as tb
from aiotieba.api.get_ats import At
from aiotieba.api.get_comments._classdef import Contents_cp
from aiotieba.api.get_posts._classdef import Contents_p, Contents_pt
from aiotieba.api.get_user_contents import UserThread

import aiotieba_reviewer as tbr
from aiotieba_reviewer.config import tomllib

tb.logging.enable_filelog()
logger = tb.get_logger()


@dcs.dataclass
class ForumCfg:
    fname: str
    key: str


with open("cmd_handler.toml", 'rb') as file:
    LISTEN_CONFIG = tomllib.load(file)
    FORUMS = [ForumCfg(**f) for f in LISTEN_CONFIG['Forum']]
    FNAME2CFG = {cfg.fname: cfg for cfg in FORUMS}


@dcs.dataclass
class Admin:
    client: tb.Client
    db: tbr.MySQLDB


@dcs.dataclass
class AdminManager:
    fname2admin: dict[str, Admin] = dcs.field(default_factory=dict)

    async def get(self, fname: str) -> Admin:
        admin = self.fname2admin.get(fname, None)

        if admin is None:
            forum_cfg = FNAME2CFG[fname]

            client = tb.Client(account=tbr.get_account(forum_cfg.key))
            await client.__aenter__()
            db = tbr.MySQLDB(fname)
            await db.__aenter__()

            admin = Admin(client, db)
            self.fname2admin[fname] = admin

        return admin


@dcs.dataclass
class CmdArgs:
    cmd: str
    args: list[str]


TypeArgParser = Callable[[str], CmdArgs]


class TypeParent(Protocol):
    @property
    def fid(self) -> int: ...

    @property
    def fname(self) -> str: ...

    @property
    def tid(self) -> int: ...

    @property
    def pid(self) -> int: ...

    @property
    def author_id(self) -> int: ...

    @property
    def contents(self) -> Contents_pt | Contents_p | Contents_cp: ...


@dcs.dataclass
class Context:
    at: At
    text: str = dcs.field(init=False, repr=False)
    admin: Admin = dcs.field(init=False, repr=False)
    cmdargs: CmdArgs = dcs.field(init=False)
    parent: TypeParent = dcs.field(default=None, init=False)
    argparser: TypeArgParser = dcs.field(init=False, repr=False)
    fullinit_success: bool = dcs.field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        self.text = self.at.text

    async def async_init(self) -> None:
        self.permission = await self.db.get_user_id(self.user.user_id)

        if len(self.at.text.encode('utf-8')) >= 78:
            await self.async_fullinit()

        self.cmdargs = self.argparser(self.text)

    async def async_fullinit(self) -> None:
        if self.fullinit_success:
            return

        if self.at.is_comment:
            await asyncio.sleep(3.0)
            comments = await self.client.get_comments(self.tid, self.pid, is_comment=True)
            self.parent = comments.post
            for comment in comments:
                if comment.pid == self.pid:
                    self.text = comment.text

        elif self.at.is_thread:
            await asyncio.sleep(3.0)
            posts = await self.client.get_posts(self.tid, rn=0)
            self.text = posts.thread.text
            share_thread = posts.thread.share_origin
            posts = await self.client.get_posts(share_thread.tid, rn=0)
            self.parent = posts.thread

        else:
            await asyncio.sleep(2.0)
            posts = await self.client.get_posts(self.tid, pn=8192, rn=20, sort=tb.enums.PostSortType.DESC)
            for post in posts:
                if post.pid == self.pid:
                    self.text = post.contents.text
                    break
            posts = await self.client.get_posts(self.tid, rn=0)
            self.parent = posts.thread

        self.cmdargs = self.argparser(self.text)
        self.fullinit_success = True

    @property
    def fname(self):
        return self.at.fname

    @property
    def tid(self):
        return self.at.tid

    @property
    def pid(self):
        return self.at.pid

    @property
    def user(self) -> tb.typing.UserInfo:
        return self.at.user

    @property
    def cmd(self) -> str:
        return self.cmdargs.cmd

    @property
    def args(self) -> list[str]:
        return self.cmdargs.args

    @property
    def client(self) -> tb.Client:
        return self.admin.client

    @property
    def db(self) -> tbr.MySQLDB:
        return self.admin.db

    @functools.cached_property
    def note(self) -> str:
        return f"cmd_{self.cmd}_by_{self.user.user_id}"


def get_num_between_two_signs(s: str, sign: str) -> int:
    if (first_sign := s.find(sign)) == -1:
        return 0
    if (last_sign := s.rfind(sign)) == -1:
        return 0
    sub_str = s[first_sign + 1 : last_sign]
    if not sub_str.isdecimal():
        return 0
    return int(sub_str)


async def arg2user_info(client: tb.Client, arg: str) -> tb.typing.UserInfo:
    if tieba_uid := get_num_between_two_signs(arg, '#'):
        user = await client.tieba_uid2user_info(tieba_uid)
    elif user_id := get_num_between_two_signs(arg, '/'):
        user = await client.get_user_info(user_id, tb.enums.ReqUInfo.BASIC)
    else:
        user = await client.get_user_info(arg, tb.enums.ReqUInfo.BASIC)

    if not user:
        raise ValueError(f"无法根据参数`{arg}`找到对应的用户")

    return user


async def delete_parent(ctx: Context) -> bool:
    await ctx.async_fullinit()

    if ctx.at.is_thread:
        if ctx.fname != ctx.parent.fname:
            raise ValueError(f"指令所在吧`{ctx.fname}`与被转发帖所在吧`{ctx.parent.fname}`不匹配")
        if ctx.parent.author_id == 0:
            raise ValueError("无法获取被转发帖的作者信息")

    logger.info(f"尝试删除父级 {ctx.parent}")

    await ctx.client.del_post(ctx.parent.fid, ctx.parent.tid, ctx.parent.pid)


def block_day_approx(day: int) -> int:
    if 1 <= day < 2:
        return 1
    elif 2 <= day < 7:
        return 3
    elif 7 <= day:
        return 10


async def block(ctx: Context, id_: str | int, day: int, reason: str = "") -> bool:
    ret = await ctx.client.block(ctx.fname, id_, day=day, reason=reason)
    if isinstance(ret.err, tb.exception.TiebaServerError):
        if ret.err.code == 3150003:
            ret = await ctx.client.block(ctx.fname, id_, day=block_day_approx(day), reason=reason)
            return ret
        elif ret.err.code == 1211068:
            await ctx.client.unblock(ctx.fname, id_)
            await asyncio.sleep(0.5)
            ret = await ctx.client.block(ctx.fname, id_, day=day, reason=reason)
            return ret

    return ret


async def set_perm(ctx: Context, user_id: int, new_perm: int, note: str) -> bool:
    target_perm, target_note, _ = await ctx.db.get_user_id_full(user_id)
    if target_perm >= ctx.permission:
        raise ValueError(f"目标用户的原权限={target_perm} 大于等于 指令发起者的权限={ctx.permission}")
    if new_perm >= ctx.permission:
        raise ValueError(f"目标用户的新权限={new_perm} 大于等于 指令发起者的权限={ctx.permission}")

    logger.info(f"吧名={ctx.fname} id={user_id} 先前的备注={target_note}")

    if new_perm != 0:
        ret = await ctx.db.add_user_id(user_id, new_perm, note=note)
    else:
        ret = await ctx.db.del_user_id(user_id)

    return ret


@dcs.dataclass
class ABCCommand:
    req_arg_num: int
    req_perm: int

    @abc.abstractmethod
    async def run(self: ABCCommand, ctx: Context) -> None: ...


@dcs.dataclass
class CMD_delete(ABCCommand):
    req_arg_num: int = 0
    req_perm: int = 20

    async def run(self: ABCCommand, ctx: Context) -> None:
        await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)
        await delete_parent(ctx)


@dcs.dataclass
class CMD_recover(ABCCommand):
    req_arg_num: int = 1
    req_perm: int = 20

    async def run(self: ABCCommand, ctx: Context) -> None:
        await ctx.async_fullinit()

        tpid = int(ctx.args[0])
        if tpid < 1e11:
            success = await ctx.client.recover_thread(ctx.fname, tpid)
        else:
            success = await ctx.client.recover_post(ctx.fname, tpid)

        if success:
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_hide(ABCCommand):
    req_arg_num: int = 0
    req_perm: int = 20

    async def run(self: ABCCommand, ctx: Context) -> None:
        if await ctx.client.hide_thread(ctx.fname, ctx.tid):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_unhide(ABCCommand):
    req_arg_num: int = 0
    req_perm: int = 20

    async def run(self: ABCCommand, ctx: Context) -> None:
        if await ctx.client.unhide_thread(ctx.fname, ctx.tid):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_block(ABCCommand):
    req_arg_num: int = 1
    req_perm: int = 20

    async def run(self: ABCCommand, ctx: Context) -> None:
        day = int(d) if (d := ctx.cmd.removeprefix('block')) else 10
        user = await arg2user_info(ctx.client, ctx.args[0])
        reason = ctx.args[1] if len(ctx.args) > 1 else ctx.note

        if await block(ctx, user.portrait, day, reason):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_unblock(ABCCommand):
    req_arg_num: int = 1
    req_perm: int = 20

    async def run(self: ABCCommand, ctx: Context) -> None:
        user = await arg2user_info(ctx.client, ctx.args[0])

        if await ctx.client.unblock(ctx.fname, user.user_id):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_drop(ABCCommand):
    req_arg_num: int = 0
    req_perm: int = 20

    async def run(self: ABCCommand, ctx: Context) -> None:
        await ctx.async_fullinit()

        day = int(d) if (d := ctx.cmd.removeprefix('drop')) else 10
        reason = ctx.args[0] if ctx.args else ctx.note

        if await block(ctx, ctx.parent.author_id, day, reason):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)
            await delete_parent(ctx)


@dcs.dataclass
class CMD_recommend(ABCCommand):
    req_arg_num: int = 0
    req_perm: int = 10

    async def run(self: ABCCommand, ctx: Context) -> None:
        if await ctx.client.recommend(ctx.fname, ctx.tid):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_move(ABCCommand):
    req_arg_num: int = 0
    req_perm: int = 20

    async def run(self: ABCCommand, ctx: Context) -> None:
        await asyncio.sleep(1.0)
        if not (threads := await ctx.client.get_threads(ctx.fname)):
            return

        from_tab_id = 0
        for thread in threads:
            if thread.tid == ctx.tid:
                from_tab_id = thread.tab_id
        to_tab_id = threads.tab_map.get(ctx.args[0], 0)

        if await ctx.client.move(ctx.fname, ctx.tid, to_tab_id=to_tab_id, from_tab_id=from_tab_id):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_good(ABCCommand):
    req_arg_num: int = 0
    req_perm: int = 20

    async def run(self: ABCCommand, ctx: Context) -> None:
        cname = ctx.args[0] if ctx.args else ''

        if await ctx.client.good(ctx.fname, ctx.tid, cname=cname):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_ungood(ABCCommand):
    req_arg_num: int = 0
    req_perm: int = 20

    async def run(self: ABCCommand, ctx: Context) -> None:
        if await ctx.client.ungood(ctx.fname, ctx.tid):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_top(ABCCommand):
    req_arg_num: int = 0
    req_perm: int = 40

    async def run(self: ABCCommand, ctx: Context) -> None:
        if await ctx.client.top(ctx.fname, ctx.tid):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_untop(ABCCommand):
    req_arg_num: int = 0
    req_perm: int = 30

    async def run(self: ABCCommand, ctx: Context) -> None:
        if await ctx.client.untop(ctx.fname, ctx.tid):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_black(ABCCommand):
    req_arg_num: int = 1
    req_perm: int = 30

    async def run(self: ABCCommand, ctx: Context) -> None:
        user = await arg2user_info(ctx.client, ctx.args[0])
        note = ctx.args[1] if len(ctx.args) > 1 else ctx.note

        if await set_perm(ctx, user.user_id, -50, note):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_white(ABCCommand):
    req_arg_num: int = 1
    req_perm: int = 30

    async def run(self: ABCCommand, ctx: Context) -> None:
        user = await arg2user_info(ctx.client, ctx.args[0])
        note = ctx.args[1] if len(ctx.args) > 1 else ctx.note

        if await set_perm(ctx, user.user_id, 10, note):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_reset(ABCCommand):
    req_arg_num: int = 1
    req_perm: int = 30

    async def run(self: ABCCommand, ctx: Context) -> None:
        user = await arg2user_info(ctx.client, ctx.args[0])

        if await set_perm(ctx, user.user_id, 0, ''):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_exdrop(ABCCommand):
    req_arg_num: int = 0
    req_perm: int = 40

    async def run(self: ABCCommand, ctx: Context) -> None:
        await ctx.async_fullinit()

        note = ctx.args[0] if ctx.args else ctx.note

        success0 = await set_perm(ctx, ctx.parent.author_id, -50, note)
        success1 = await block(ctx, ctx.parent.author_id, 90, note)
        if success0 and success1:
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)
        await delete_parent(ctx)


@dcs.dataclass
class CMD_avada_kedavra(ABCCommand):
    req_arg_num: int = 0
    req_perm: int = 50

    async def run(self: ABCCommand, ctx: Context) -> None:
        await ctx.async_fullinit()

        note = ctx.args[0] if ctx.args else ctx.note

        success0 = await set_perm(ctx, ctx.parent.author_id, -50, note)
        success1 = await block(ctx, ctx.parent.author_id, 90, note)
        if success0 and success1:
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)

        dthreads: list[UserThread] = []
        for pn in range(1, 0xFFFF):
            threads = await ctx.client.get_user_threads(ctx.parent.author_id, pn)
            for thread in threads:
                if thread.fname != ctx.fname:
                    continue
                dthreads.append(thread)
            if len(threads) < 60:
                break
        for thread in dthreads:
            await ctx.client.del_post(thread.fid, thread.tid, thread.pid)


@dcs.dataclass
class CMD_set(ABCCommand):
    req_arg_num: int = 2
    req_perm: int = 30

    async def run(self: ABCCommand, ctx: Context) -> None:
        user = await arg2user_info(ctx.client, ctx.args[0])
        new_perm = int(ctx.args[1])
        note = ctx.args[2] if len(ctx.args) > 2 else ctx.note

        if await set_perm(ctx, user.user_id, new_perm, note):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_get(ABCCommand):
    req_arg_num: int = 1
    req_perm: int = 10

    async def run(self: ABCCommand, ctx: Context) -> None:
        user = await arg2user_info(ctx.client, ctx.args[0])
        user = await ctx.client.get_user_info(user.user_id)
        if user.user_id:
            record = await ctx.db.get_user_id_full(user.user_id)
            logger.info(f"用户权限级别={record[0]}\n备注={record[1]}\n被记录的时间={record[2]}\n详细用户信息={user!r}")
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)
        else:
            raise ValueError("无法获取用户信息 可能是因为用户已注销或被屏蔽")


@dcs.dataclass
class CMD_tb_black(ABCCommand):
    req_arg_num: int = 1
    req_perm: int = 40

    async def run(self: ABCCommand, ctx: Context) -> None:
        user = await arg2user_info(ctx.client, ctx.args[0])

        if await ctx.client.add_bawu_blacklist(ctx.fname, user.user_id):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_tb_reset(ABCCommand):
    req_arg_num: int = 1
    req_perm: int = 30

    async def run(self: ABCCommand, ctx: Context) -> None:
        user = await arg2user_info(ctx.client, ctx.args[0])

        if await ctx.client.del_bawu_blacklist(ctx.fname, user.user_id):
            await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


@dcs.dataclass
class CMD_ping(ABCCommand):
    req_arg_num: int = 0
    req_perm: int = 10

    async def run(self: ABCCommand, ctx: Context) -> None:
        await ctx.client.del_post(ctx.fname, ctx.tid, ctx.pid)


def get_cmd_map() -> dict[str, type[ABCCommand]]:
    cmd_map = {}
    for subcls in ABCCommand.__subclasses__():
        clsname = subcls.__name__
        cmd_map[clsname.removeprefix('CMD_')] = subcls
    return cmd_map


CMD_MAP = get_cmd_map()


def default_last_exec_time() -> int:
    return int(time.time()) - 3600 * 12


@dcs.dataclass
class Executer:
    listener: tb.Client = dcs.field(init=False)
    admin_manager: AdminManager = dcs.field(init=False)
    argparser: TypeArgParser = dcs.field(init=False)
    last_exec_time: int = dcs.field(default_factory=default_last_exec_time)

    def __post_init__(self) -> None:
        self.listener = tb.Client(account=tbr.get_account(LISTEN_CONFIG['listener']))
        self.admin_manager = AdminManager()

    async def __aenter__(self) -> Executer:
        await self.listener.__aenter__()

        listener_userinfo = await self.listener.get_self_info(tb.ReqUInfo.USER_NAME)
        subexp = re.compile(f".*?@{listener_userinfo.user_name}")

        def argparser(text: str) -> CmdArgs:
            text = subexp.sub('', text, count=1)

            args = [arg.lstrip(' ') for arg in text.split(' ') if arg]
            if args:
                cmd = args[0]
                args = args[1:]
            else:
                cmd = ''
                args = []

            return CmdArgs(cmd, args)

        self.argparser = argparser

        return self

    async def __aexit__(self, exc_type=None, exc_val=None, exc_tb=None) -> None:
        await self.listener.__aexit__()
        await asyncio.gather(*[c.__aexit__() for c in itertools.chain.from_iterable(self.admin_manager.fname2admin)])

    async def run(self) -> None:
        try:
            while 1:
                asyncio.create_task(self.__fetch_and_exec_cmds())
                logger.debug('heartbeat')
                await asyncio.sleep(4.0)

        except asyncio.CancelledError:
            return
        except Exception:
            logger.critical("意料之外的错误", exc_info=True)
            return

    async def __fetch_and_exec_cmds(self) -> None:
        ats = await self.listener.get_ats()

        ats = list(itertools.takewhile(lambda at: at.create_time > self.last_exec_time, ats))

        if ats:
            self.last_exec_time = ats[0].create_time
            await asyncio.gather(*[self._execute_cmd(at) for at in ats])

    async def _execute_cmd(self, at: At) -> None:
        try:
            ctx = Context(at)
            admin = await self.admin_manager.get(ctx.fname)
            ctx.admin = admin
            ctx.argparser = self.argparser

            async with asyncio.timeout(60.0):
                await ctx.async_init()

                logger.info(f"尝试执行指令='{ctx.text}' 发起者={ctx.user.log_name}")

                meta_cmd = re.search(r'[a-z_]+[^\d]', ctx.cmd).group(0)
                if meta_cmd not in CMD_MAP:
                    raise ValueError("指令不存在")
                cmd = CMD_MAP[meta_cmd]()

                if len(ctx.args) < cmd.req_arg_num:
                    raise ValueError(f"参数量不足. 期望数量={cmd.req_arg_num}")
                if ctx.permission < cmd.req_perm:
                    raise ValueError(f"权限不足. 最低权限需求={cmd.req_perm} 指令发起者权限={ctx.permission}")

                await cmd.run(ctx)

        except Exception as err:
            logger.error(f"{err}. 发起者={ctx.user.log_name} cmd={ctx.cmd} args={ctx.args} at={ctx.at}")


if __name__ == '__main__':

    async def main():
        async with Executer() as executer:
            await executer.run()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

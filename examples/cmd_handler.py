import asyncio
import functools
import itertools
import re
import time
from typing import Protocol, Tuple, Union

import aiotieba as tb
import async_timeout
from aiotieba.api.get_ats import At
from aiotieba.api.get_comments._classdef import Contents_cp
from aiotieba.api.get_posts._classdef import Contents_p, Contents_pt
from aiotieba.config import tomllib
from aiotieba.logging import get_logger as LOG

import aiotieba_reviewer as tbr

tb.logging.enable_filelog()

with open("cmd_handler.toml", 'rb') as file:
    LISTEN_CONFIG = tomllib.load(file)
    FORUMS = {f['fname']: f for f in LISTEN_CONFIG['Forum']}
    del LISTEN_CONFIG['Forum']


class TimerRecorder(object):
    """
    时间记录器

    Args:
        shift_sec (float): 启动时允许解析shift_sec秒之前的at
        post_interval (float): 两次post_add之间需要的间隔秒数

    Attributes:
        last_parse_time (float): 上次解析at信息的时间(以百度服务器为准)
        last_post_time (float): 上次发送回复的时间(以百度服务器为准)
        post_interval (float): 两次post_add之间需要的时间间隔
    """

    __slots__ = ['last_parse_time', 'last_post_time', 'post_interval']

    def __init__(self, shift_sec: float, post_interval: float) -> None:
        self.last_post_time: float = 0
        self.post_interval: float = post_interval
        self.last_parse_time: float = time.time() - shift_sec

    def is_inrange(self, check_time: int) -> bool:
        return self.last_parse_time < check_time

    def allow_execute(self) -> bool:
        current_time = time.time()

        if current_time - self.last_post_time > self.post_interval:
            self.last_post_time = current_time
            return True

        return False


class TypeParent(Protocol):
    @property
    def fid(self) -> int:
        ...

    @property
    def fname(self) -> str:
        ...

    @property
    def tid(self) -> int:
        ...

    @property
    def pid(self) -> int:
        ...

    @property
    def author_id(self) -> int:
        ...

    @property
    def contents(self) -> Union[Contents_pt, Contents_p, Contents_cp]:
        ...


class Context(object):
    __slots__ = [
        'at',
        'text',
        'admin',
        'admin_db',
        'speaker',
        '_init_full_success',
        '_args',
        '_cmd_type',
        '_note',
        'permission',
        'parent',
    ]

    def __init__(self, at: At) -> None:
        self.at: At = at
        self.text = at.text
        self.parent: TypeParent = None

        self.admin: tb.Client = None
        self.admin_db: tbr.MySQLDB = None
        self.speaker: tb.Client = None

        self._init_full_success: bool = False
        self._args = None
        self._cmd_type = None
        self._note = None
        self.permission: int = 0

    async def _init(self) -> bool:
        self.permission = await self.admin_db.get_user_id(self.user.user_id)

        if len(self.at.text.encode('utf-8')) >= 78:
            await self.init_full()

        self.__init_args()
        return True

    async def init_full(self) -> bool:
        if self._init_full_success:
            return True

        if self.at.is_comment:
            await asyncio.sleep(3.0)
            comments = await self.admin.get_comments(self.tid, self.pid, is_comment=True)
            self.parent = comments.post
            for comment in comments:
                if comment.pid == self.pid:
                    self.text = comment.text

        elif self.at.is_thread:
            await asyncio.sleep(3.0)
            posts = await self.admin.get_posts(self.tid, rn=0)
            self.text = posts.thread.text
            share_thread = posts.thread.share_origin
            posts = await self.admin.get_posts(share_thread.tid, rn=0)
            self.parent = posts.thread

        else:
            await asyncio.sleep(2.0)
            posts = await self.admin.get_posts(self.tid, pn=8192, rn=20, sort=tb.enums.PostSortType.DESC)
            for post in posts:
                if post.pid == self.pid:
                    self.text = post.contents.text
                    break
            posts = await self.admin.get_posts(self.tid, rn=0)
            self.parent = posts.thread

        self.__init_args()
        self._init_full_success = True

        return True

    def __init_args(self) -> None:
        self._args = []
        self._cmd_type = ''

        text = re.sub(r'.*?@.*? ', '', self.text, count=1)

        self._args = [arg.lstrip(' ') for arg in text.split(' ')]
        if self._args:
            self._cmd_type = self._args[0]
            self._args = self._args[1:]

    @property
    def cmd_type(self) -> str:
        if self._cmd_type is None:
            self.__init_args()
        return self._cmd_type

    @property
    def args(self) -> list[str]:
        if self._args is None:
            self.__init_args()
        return self._args

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
    def note(self) -> str:
        if self._note is None:
            self._note = f"cmd_{self.cmd_type}_by_{self.user.user_id}"
        return self._note


def check_and_log(need_permission: int = 0, need_arg_num: int = 0):
    """
    装饰器实现鉴权和参数数量检查

    Args:
        need_permission (int, optional): 需要的权限级别
        need_arg_num (bool, optional): 需要的参数数量
    """

    def wrapper(func):
        @functools.wraps(func)
        async def _(self: "Listener", ctx: Context) -> None:
            try:
                ctx.admin, ctx.admin_db, ctx.speaker = await self.get_admin(ctx.fname)

                await ctx._init()
                LOG().info(f"user={ctx.user} type={ctx.cmd_type} args={ctx.args} tid={ctx.tid}")

                if len(ctx.args) < need_arg_num:
                    raise ValueError("参数量不足")
                if ctx.permission < need_permission:
                    raise ValueError("权限不足")

                await func(self, ctx)

            except Exception as err:
                LOG().error(err)

        return _

    return wrapper


class Listener(object):
    __slots__ = [
        'listener',
        'admins',
        'time_recorder',
    ]

    def __init__(self) -> None:
        self.listener = tb.Client(LISTEN_CONFIG['listener'])
        self.admins = {}
        self.time_recorder = TimerRecorder(3600 * 12, 10)

    async def __aenter__(self) -> "Listener":
        await self.listener.__aenter__()
        return self

    async def __aexit__(self, exc_type=None, exc_val=None, exc_tb=None) -> None:
        await asyncio.gather(
            *[c.__aexit__() for c in itertools.chain.from_iterable(self.admins.values())], self.listener.__aexit__()
        )

    async def run(self) -> None:
        while 1:
            try:
                asyncio.create_task(self.__fetch_and_execute_cmds())
                LOG().debug('heartbeat')
                await asyncio.sleep(4.0)

            except asyncio.CancelledError:
                return
            except Exception:
                LOG().critical("Unhandled error", exc_info=True)
                return

    async def get_admin(self, fname: str) -> Tuple[tb.Client, tbr.MySQLDB, tb.Client]:
        tup = self.admins.get(fname)

        if tup is None:
            cfg = FORUMS.get(fname)
            if cfg is None:
                raise ValueError(f"找不到管理员. fname={fname}")

            admin = tb.Client(cfg['admin'])
            await admin.__aenter__()
            admin_db = tbr.MySQLDB(fname)
            await admin_db.__aenter__()
            speaker = tb.Client(cfg['speaker'])
            await speaker.__aenter__()

            tup = admin, admin_db, speaker
            self.admins[fname] = tup

        return tup

    async def __fetch_and_execute_cmds(self) -> None:
        ats = await self.listener.get_ats()

        ats = list(itertools.takewhile(lambda at: self.time_recorder.is_inrange(at.create_time), ats))

        if ats:
            self.time_recorder.last_parse_time = ats[0].create_time
            await asyncio.gather(*[self._execute_cmd(at) for at in ats])

    async def _execute_cmd(self, at: At) -> None:
        async with async_timeout.timeout(120.0):
            ctx = Context(at)
            cmd_func = getattr(self, f'cmd_{ctx.cmd_type}', self.cmd_default)
            await cmd_func(ctx)

    @staticmethod
    def get_num_between_two_signs(s: str, sign: str) -> int:
        if (first_sign := s.find(sign)) == -1:
            return 0
        if (last_sign := s.rfind(sign)) == -1:
            return 0
        sub_str = s[first_sign + 1 : last_sign]
        if not sub_str.isdecimal():
            return 0
        return int(sub_str)

    async def __arg2user_info(self, arg: str) -> tb.typing.UserInfo:
        if tieba_uid := self.get_num_between_two_signs(arg, '#'):
            user = await self.listener.tieba_uid2user_info(tieba_uid)
        elif user_id := self.get_num_between_two_signs(arg, '/'):
            user = await self.listener.get_user_info(user_id, tb.enums.ReqUInfo.BASIC)
        else:
            user = await self.listener.get_user_info(arg, tb.enums.ReqUInfo.BASIC)

        if not user:
            raise ValueError("找不到对应的用户")

        return user

    async def __cmd_set(self, ctx: Context, new_permission: int, note: str, user_id: int = 0) -> bool:
        """
        设置权限级别
        """

        if user_id == 0:
            user = await self.__arg2user_info(ctx.args[0])
            user_id = user.user_id

        old_permission, old_note, _ = await ctx.admin_db.get_user_id_full(user_id)
        if old_permission >= ctx.permission:
            raise ValueError("原权限大于等于操作者权限")
        if new_permission >= ctx.permission:
            raise ValueError("新权限大于等于操作者权限")

        LOG().info(f"forum={ctx.fname} user_id={user_id} old_note={old_note}")

        if new_permission != 0:
            success = await ctx.admin_db.add_user_id(user_id, new_permission, note=note)
        else:
            success = await ctx.admin_db.del_user_id(user_id)

        return success

    @check_and_log(need_permission=2, need_arg_num=0)
    async def cmd_delete(self, ctx: Context) -> None:
        """
        delete指令
        删帖
        """

        await self.__cmd_drop(ctx)

    @check_and_log(need_permission=2, need_arg_num=1)
    async def cmd_recover(self, ctx: Context) -> None:
        """
        recover指令
        恢复删帖
        """

        await ctx.init_full()

        _id = ctx.args[0]
        _id = _id[_id.rfind('#') + 1 :]
        _id = int(_id)

        if _id < 1e11:
            success = await ctx.admin.recover_thread(ctx.fname, _id)
        else:
            success = await ctx.admin.recover_post(ctx.fname, _id)

        if success:
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=2, need_arg_num=0)
    async def cmd_hide(self, ctx: Context) -> None:
        """
        hide指令
        屏蔽指令所在主题帖
        """

        if await ctx.admin.hide_thread(ctx.fname, ctx.tid):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=2, need_arg_num=0)
    async def cmd_unhide(self, ctx: Context) -> None:
        """
        unhide指令
        解除指令所在主题帖的屏蔽
        """

        if await ctx.admin.unhide_thread(ctx.fname, ctx.tid):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=2, need_arg_num=1)
    async def cmd_block(self, ctx: Context) -> None:
        """
        block指令
        通过id封禁对应用户10天
        """

        await self.__cmd_block(ctx, 10)

    @check_and_log(need_permission=2, need_arg_num=1)
    async def cmd_block3(self, ctx: Context) -> None:
        """
        block3指令
        通过id封禁对应用户3天
        """

        await self.__cmd_block(ctx, 3)

    @check_and_log(need_permission=2, need_arg_num=1)
    async def cmd_block1(self, ctx: Context) -> None:
        """
        block1指令
        通过id封禁对应用户1天
        """

        await self.__cmd_block(ctx, 1)

    async def __cmd_block(self, ctx: Context, day: int) -> None:
        """
        封禁用户
        """

        user = await self.__arg2user_info(ctx.args[0])
        note = ctx.args[1] if len(ctx.args) > 1 else ctx.note

        if await ctx.admin.block(ctx.fname, user.portrait, day=day, reason=note):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=2, need_arg_num=1)
    async def cmd_unblock(self, ctx: Context) -> None:
        """
        unblock指令
        通过id解封用户
        """

        user = await self.__arg2user_info(ctx.args[0])

        if await ctx.admin.unblock(ctx.fname, user.user_id):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=2, need_arg_num=0)
    async def cmd_drop(self, ctx: Context) -> None:
        """
        drop指令
        删帖并封10天
        """

        await self.__cmd_drop(ctx, 10)

    @check_and_log(need_permission=2, need_arg_num=0)
    async def cmd_drop3(self, ctx: Context) -> None:
        """
        drop3指令
        删帖并封3天
        """

        await self.__cmd_drop(ctx, 3)

    @check_and_log(need_permission=2, need_arg_num=0)
    async def cmd_drop1(self, ctx: Context) -> None:
        """
        drop1指令
        删帖并封1天
        """

        await self.__cmd_drop(ctx, 1)

    async def __cmd_drop(self, ctx: Context, day: int = 0) -> None:
        """
        封禁用户并删除父级
        """

        await ctx.init_full()

        note = ctx.args[0] if len(ctx.args) > 0 else ctx.note

        LOG().info(f"Try to del {ctx.parent.__class__.__name__}. parent={ctx.parent} user_id={ctx.parent.author_id}")

        if ctx.at.is_thread:
            if ctx.fname != ctx.parent.fname:
                raise ValueError("被转发帖不来自同一个吧")
            if ctx.parent.author_id == 0:
                raise ValueError("无法获取被转发帖的作者信息")

        await ctx.admin.del_post(ctx.parent.fid, ctx.parent.tid, ctx.parent.pid)
        await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)
        if day:
            await ctx.admin.block(ctx.parent.fid, ctx.parent.author_id, day=day, reason=note)

    @check_and_log(need_permission=1, need_arg_num=0)
    async def cmd_recommend(self, ctx: Context) -> None:
        """
        recommend指令
        对指令所在主题帖执行“大吧主首页推荐”操作
        """

        if await ctx.admin.recommend(ctx.fname, ctx.tid):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=2, need_arg_num=1)
    async def cmd_move(self, ctx: Context) -> None:
        """
        move指令
        将指令所在主题帖移动至名为tab_name的分区
        """

        if not (threads := await self.listener.get_threads(ctx.fname)):
            return

        from_tab_id = 0
        for thread in threads:
            if thread.tid == ctx.tid:
                from_tab_id = thread.tab_id
        to_tab_id = threads.tab_map.get(ctx.args[0], 0)

        if await ctx.admin.move(ctx.fname, ctx.tid, to_tab_id=to_tab_id, from_tab_id=from_tab_id):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=2, need_arg_num=0)
    async def cmd_good(self, ctx: Context) -> None:
        """
        good指令
        将指令所在主题帖加到以cname为名的精华分区。cname默认为''即不分区
        """

        cname = ctx.args[0] if len(ctx.args) else ''

        if await ctx.admin.good(ctx.fname, ctx.tid, cname=cname):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=2, need_arg_num=0)
    async def cmd_ungood(self, ctx: Context) -> None:
        """
        ungood指令
        撤销指令所在主题帖的精华
        """

        if await ctx.admin.ungood(ctx.fname, ctx.tid):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=4, need_arg_num=0)
    async def cmd_top(self, ctx: Context) -> None:
        """
        top指令
        置顶指令所在主题帖
        """

        if await ctx.admin.top(ctx.fname, ctx.tid):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=4, need_arg_num=0)
    async def cmd_untop(self, ctx: Context) -> None:
        """
        untop指令
        撤销指令所在主题帖的置顶
        """

        if await ctx.admin.untop(ctx.fname, ctx.tid):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=4, need_arg_num=1)
    async def cmd_black(self, ctx: Context) -> None:
        """
        black指令
        将id加入脚本黑名单
        """

        note = ctx.args[1] if len(ctx.args) > 1 else ctx.note

        if await self.__cmd_set(ctx, -5, note):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=3, need_arg_num=1)
    async def cmd_white(self, ctx: Context) -> None:
        """
        white指令
        将id加入脚本白名单
        """

        note = ctx.args[1] if len(ctx.args) > 1 else ctx.note

        if await self.__cmd_set(ctx, 1, note):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=3, need_arg_num=1)
    async def cmd_reset(self, ctx: Context) -> None:
        """
        reset指令
        将id移出脚本名单
        """

        note = ctx.args[1] if len(ctx.args) > 1 else ctx.note

        if await self.__cmd_set(ctx, 0, note):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=4, need_arg_num=0)
    async def cmd_exdrop(self, ctx: Context) -> None:
        """
        exdrop指令
        删帖并将发帖人加入脚本黑名单+封禁十天
        """

        await self.__cmd_drop(ctx, 10)

        note = ctx.args[0] if len(ctx.args) > 0 else ctx.note

        await self.__cmd_set(ctx, -5, note, user_id=ctx.parent.author_id)

    @check_and_log(need_permission=5, need_arg_num=0)
    async def cmd_avada_kedavra(self, ctx: Context) -> None:
        """
        索命咒
        删帖 清空发帖人主页显示的在当前吧的所有主题帖 加入脚本黑名单+封禁十天
        """

        await self.__cmd_drop(ctx, 10)

        note = ctx.args[0] if len(ctx.args) > 0 else ctx.note
        user_id = ctx.parent.author_id
        await self.__cmd_set(ctx, -5, note, user_id=user_id)

        for pn in range(1, 0xFFFF):
            threads = await ctx.admin.get_user_threads(user_id, pn)
            for thread in threads:
                if thread.fname != ctx.fname:
                    continue
                await ctx.admin.del_post(thread.fid, thread.tid, thread.pid)

    @check_and_log(need_permission=4, need_arg_num=2)
    async def cmd_set(self, ctx: Context) -> None:
        """
        set指令
        设置用户的权限级别
        """

        new_permission = int(ctx.args[1])
        note = ctx.args[2] if len(ctx.args) > 2 else ctx.note

        if await self.__cmd_set(ctx, new_permission, note):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=0, need_arg_num=1)
    async def cmd_get(self, ctx: Context) -> None:
        """
        get指令
        获取用户的个人信息与标记信息
        """

        if not self.time_recorder.allow_execute():
            raise ValueError("speaker尚未冷却完毕")

        user = await self.__arg2user_info(ctx.args[0])

        permission, note, record_time = await ctx.admin_db.get_user_id_full(user.user_id)
        msg_content = f"""user_name: {user.user_name}\nuser_id: {user.user_id}\nportrait: {user.portrait}\npermission: {permission}\nnote: {note}\nrecord_time: {record_time.strftime("%Y-%m-%d %H:%M:%S")}"""

        if await ctx.speaker.send_msg(ctx.user.user_id, msg_content):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=4, need_arg_num=2)
    async def cmd_img_set(self, ctx: Context) -> None:
        """
        img_set指令
        设置图片的封锁级别
        """

        await ctx.init_full()
        imgs = ctx.parent.contents.imgs

        if len(ctx.args) > 2:
            index = int(ctx.args[0])
            imgs = imgs[index - 1 : index]
            permission = int(ctx.args[1])
            note = ctx.args[2]
        else:
            permission = int(ctx.args[0])
            note = ctx.args[1]

        for img in imgs:
            image = await self.listener.get_image(img.src)
            if image is None:
                continue
            img_hash = tbr.imgproc.compute_imghash(image)
            if img_hash == 4412820541203793671:
                continue

            await ctx.admin_db.add_imghash(img_hash, img.hash, permission=permission, note=note)

        await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=3, need_arg_num=0)
    async def cmd_img_reset(self, ctx: Context) -> None:
        """
        img_reset指令
        重置图片的封锁级别
        """

        await ctx.init_full()
        imgs = ctx.parent.contents.imgs

        if ctx.args:
            index = int(ctx.args[0])
            imgs = imgs[index - 1 : index]

        for img in imgs:
            image = await self.listener.get_image(img.src)
            if image is None:
                continue
            img_hash = tbr.imgproc.compute_imghash(image)

            await ctx.admin_db.del_imghash(img_hash)

        await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=1, need_arg_num=0)
    async def cmd_recom_status(self, ctx: Context) -> None:
        """
        recom_status指令
        获取大吧主推荐功能的月度配额状态
        """

        if not self.time_recorder.allow_execute():
            raise ValueError("speaker尚未冷却完毕")

        status = await ctx.admin.get_recom_status(ctx.fname)
        percent = status.used_recom_num / status.total_recom_num * 100
        content = f"Used: {status.used_recom_num} / {status.total_recom_num} = {percent:.2f}%"

        if await ctx.speaker.send_msg(ctx.user.user_id, content):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=4, need_arg_num=1)
    async def cmd_tb_black(self, ctx: Context) -> None:
        """
        tb_black指令
        将id加入贴吧黑名单
        """

        user = await self.__arg2user_info(ctx.args[0])

        if await ctx.admin.add_bawu_blacklist(ctx.fname, user.user_id):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=3, need_arg_num=1)
    async def cmd_tb_reset(self, ctx: Context) -> None:
        """
        tb_reset指令
        将id移出贴吧黑名单
        """

        user = await self.__arg2user_info(ctx.args[0])

        if await ctx.admin.del_bawu_blacklist(ctx.fname, user.user_id):
            await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=1, need_arg_num=0)
    async def cmd_ping(self, ctx: Context) -> None:
        """
        ping指令
        用于测试bot可用性的空指令
        """

        await ctx.admin.del_post(ctx.fname, ctx.tid, ctx.pid)

    @check_and_log(need_permission=129, need_arg_num=65536)
    async def cmd_default(self, _: Context) -> None:
        """
        default指令
        """

        pass


if __name__ == '__main__':

    async def main():
        async with Listener() as listener:
            await listener.run()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

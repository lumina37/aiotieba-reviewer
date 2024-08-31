from __future__ import annotations

import datetime
import logging
import ssl
from collections.abc import Callable
from typing import Any, Final

import asyncpg
import asyncpg.prepared_stmt
from aiotieba import get_logger

from ..config import DB_CONFIG


def _handle_exception(
    create_table_func: Callable[[PostgreDB], None],
    null_factory: Callable[[], Any],
    ok_log_level: int = logging.NOTSET,
    err_log_level: int = logging.WARNING,
):
    """
    处理SQL操作抛出的异常 只能用于装饰类成员函数

    Args:
        create_table_func (Callable[[PostgreDB], None]): 在无法连接数据库或表不存在时执行自动建表
        null_factory (Callable[[], Any]): 空构造工厂 用于返回一个默认值
        ok_log_level (int, optional): 正常日志等级. Defaults to logging.NOTSET.
        err_log_level (int, optional): 异常日志等级. Defaults to logging.WARNING.
    """

    def wrapper(func):
        async def awrapper(self: PostgreDB, *args, **kwargs):
            def _log(log_level: int, err: Exception | None = None) -> None:
                logger = get_logger()
                if logger.isEnabledFor(err_log_level):
                    if err is None:
                        err = "Suceeded"
                    log_str = f"{err}. fname={self.fname} args={args} kwargs={kwargs}"
                    record = logger.makeRecord(logger.name, log_level, None, 0, log_str, None, None, func.__name__)
                    logger.handle(record)

            try:
                ret = await func(self, *args, **kwargs)

                if ok_log_level:
                    _log(ok_log_level)

            except Exception as err:
                _log(err_log_level, err)

                try:
                    logger = get_logger()
                    if isinstance(err, asyncpg.exceptions.InvalidCatalogNameError):
                        logger.warning("无法连接数据库 将尝试自动建库")
                        await self.create_database()
                        await create_table_func(self)
                    elif isinstance(err, asyncpg.exceptions.UndefinedTableError):
                        logger.warning("表不存在 将尝试自动建表")
                        await create_table_func(self)
                except Exception:
                    pass

                ret = null_factory()
                return ret

            else:
                return ret

        return awrapper

    return wrapper


class PostgreDB:
    """
    PostgreSQL交互

    Args:
        fname (str): 操作的目标贴吧名. Defaults to ''.

    Attributes:
        fname (str): 操作的目标贴吧名

    Note:
        容器特点: 读多写少 允许外部访问 数据安全性好
        一般用于数据持久化
    """

    __slots__ = ['fname', '_pool']

    _default_database: Final[str] = 'aiotieba'
    _default_minsize: Final[int] = 0
    _default_maxsize: Final[int] = 12
    _default_max_inactive_connection_lifetime: Final[int] = 28800

    def __init__(self, fname: str = '') -> None:
        self.fname = fname
        self._pool: asyncpg.Pool = None

    async def __aenter__(self) -> PostgreDB:
        await self._create_pool()
        return self

    async def __aexit__(self, exc_type=None, exc_val=None, exc_tb=None) -> None:
        if self._pool is not None:
            await self._pool.close()

    async def _create_pool(self) -> None:
        """
        创建连接池
        """

        ssl_ctx = None
        if cafile := DB_CONFIG.get('ssl_cafile'):
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_ctx.load_verify_locations(cafile=cafile)

        self._pool: asyncpg.Pool = await asyncpg.create_pool(
            user=DB_CONFIG['user'],
            password=DB_CONFIG.get('password', None),
            database=DB_CONFIG.get('database', self._default_database),
            min_size=DB_CONFIG.get('min_size', self._default_minsize),
            max_size=DB_CONFIG.get('max_size', self._default_maxsize),
            max_inactive_connection_lifetime=DB_CONFIG.get(
                'max_inactive_connection_lifetime', self._default_max_inactive_connection_lifetime
            ),
            host=DB_CONFIG.get('host', None),
            port=DB_CONFIG.get('port', None),
            ssl=ssl_ctx,
        )

    async def create_database(self) -> bool:
        """
        创建并初始化数据库

        Returns:
            bool: 操作是否成功
        """

        try:
            ssl_ctx = None
            if cafile := DB_CONFIG.get('ssl_cafile'):
                ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_ctx.load_verify_locations(cafile=cafile)

            conn: asyncpg.Connection = await asyncpg.connect(
                user=DB_CONFIG['user'],
                password=DB_CONFIG.get('password', None),
                host=DB_CONFIG.get('host', None),
                port=DB_CONFIG.get('port', None),
                database='postgres',
                ssl=ssl_ctx,
            )

            db_name = DB_CONFIG.get('database', self._default_database)
            await conn.execute(f'CREATE DATABASE "{db_name}"')

            await self._create_pool()
            await conn.close()

        except asyncpg.exceptions.PostgresError as err:
            get_logger().warning(f"{err}. 请检查配置文件中的`Database`字段是否填写正确")
            return False

        get_logger().info(f"成功创建并初始化数据库. db_name={db_name}")
        return True

    @_handle_exception(lambda _: None, bool, ok_log_level=logging.INFO)
    async def create_table_forum_score(self) -> bool:
        """
        创建表forum_score
        """

        async with self._pool.acquire() as conn:
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS forum_score"
                "(fid INT PRIMARY KEY, fname VARCHAR(36) NOT NULL DEFAULT '', post SMALLINT NOT NULL DEFAULT 0, follow SMALLINT NOT NULL DEFAULT 0, record_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);"
                "CREATE INDEX forum_score_fname ON forum_score(fname);"
                "CREATE INDEX forum_score_post ON forum_score(post);"
                "CREATE INDEX forum_score_follow ON forum_score(follow);"
                "CREATE INDEX forum_score_record_time ON forum_score(record_time);"
            )

        return True

    @_handle_exception(create_table_forum_score, bool, ok_log_level=logging.INFO)
    async def add_forum_score(self, fid: int, fname: str = '', /, post: int = 0, follow: int = 0) -> bool:
        """
        将fid添加到表forum_score

        Args:
            fid (int): 吧id
            fname (str): 吧名. Defaults to ''.
            post (int, optional): 发帖评分. Defaults to 0.
            follow (int, optional): 关注评分. Defaults to 0.

        Returns:
            bool: True成功 False失败
        """

        if not fid:
            raise ValueError("fid为空")

        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""INSERT INTO forum_score VALUES ({fid},'{fname}',{post},{follow},DEFAULT)"""
                "ON CONFLICT (fid) DO UPDATE SET (fname,post,follow,record_time)=(EXCLUDED.fname,EXCLUDED.post,EXCLUDED.follow,EXCLUDED.record_time);"
            )

        return True

    @_handle_exception(create_table_forum_score, bool, ok_log_level=logging.INFO)
    async def del_forum_score(self, fid: int) -> bool:
        """
        从表forum_score中删除fid

        Args:
            fid (int): 吧id

        Returns:
            bool: True成功 False失败
        """

        async with self._pool.acquire() as conn:
            await conn.execute(f"DELETE FROM forum_score WHERE fid={fid}")

        return True

    @staticmethod
    def _default_forum_score() -> tuple[int, int]:
        return (0, 0)

    @_handle_exception(create_table_forum_score, _default_forum_score)
    async def get_forum_score(self, fid: int) -> tuple[int, int]:
        """
        获取表forum_score中fid的评分

        Args:
            fid (int): 吧id

        Returns:
            tuple[int, int]: 发帖评分, 关注评分
        """

        async with self._pool.acquire() as conn:
            stmt = await conn.prepare("SELECT post,follow FROM forum_score WHERE fid=$1")
            if res := await stmt.fetchrow(fid):
                return tuple(res)

        return self._default_forum_score()

    @_handle_exception(lambda _: None, bool, ok_log_level=logging.INFO)
    async def create_table_user_id(self) -> bool:
        """
        创建表user_id_{fname}
        """

        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""CREATE TABLE IF NOT EXISTS "user_id_{self.fname}\""""
                "(user_id BIGINT PRIMARY KEY, permission SMALLINT NOT NULL DEFAULT 0, note VARCHAR(64) NOT NULL DEFAULT '', record_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);"
                f"CREATE INDEX user_id_{self.fname}_permission ON user_id_{self.fname}(permission);"
                f"CREATE INDEX user_id_{self.fname}_record_time ON user_id_{self.fname}(record_time);"
            )

        return True

    @_handle_exception(create_table_user_id, bool, ok_log_level=logging.INFO)
    async def add_user_id(self, user_id: int, /, permission: int = 0, *, note: str = '') -> bool:
        """
        将user_id添加到表user_id_{fname}

        Args:
            user_id (int): 用户的user_id
            permission (int, optional): 权限级别. Defaults to 0.
            note (str, optional): 备注. Defaults to ''.

        Returns:
            bool: True成功 False失败
        """

        if not user_id:
            raise ValueError("user_id为空")

        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""INSERT INTO "user_id_{self.fname}" VALUES ({user_id},{permission},'{note}',DEFAULT)"""
                "ON CONFLICT (user_id) DO UPDATE SET (permission,note,record_time)=(EXCLUDED.permission,EXCLUDED.note,EXCLUDED.record_time)"
            )

        return True

    @_handle_exception(create_table_user_id, bool, ok_log_level=logging.INFO)
    async def del_user_id(self, user_id: int) -> bool:
        """
        从表user_id_{fname}中删除user_id

        Args:
            user_id (int): 用户的user_id

        Returns:
            bool: True成功 False失败
        """

        async with self._pool.acquire() as conn:
            await conn.execute(f"""DELETE FROM "user_id_{self.fname}" WHERE user_id={user_id}""")

        return True

    @_handle_exception(create_table_user_id, int)
    async def get_user_id(self, user_id: int) -> int:
        """
        获取表user_id_{fname}中user_id的权限级别

        Args:
            user_id (int): 用户的user_id

        Returns:
            int: 权限级别
        """

        async with self._pool.acquire() as conn:
            stmt = await conn.prepare(f"""SELECT permission FROM "user_id_{self.fname}" WHERE user_id=$1""")
            if res := await stmt.fetchval(user_id):
                return res

        return 0

    @staticmethod
    def _default_user_id_full() -> tuple[int, str, datetime.datetime]:
        return (0, '', datetime.datetime(1970, 1, 1))

    @_handle_exception(create_table_user_id, _default_user_id_full)
    async def get_user_id_full(self, user_id: int) -> tuple[int, str, datetime.datetime]:
        """
        获取表user_id_{fname}中user_id的完整信息

        Args:
            user_id (int): 用户的user_id

        Returns:
            tuple[int, str, datetime.datetime]: 权限级别, 备注, 记录时间
        """

        async with self._pool.acquire() as conn:
            stmt = await conn.prepare(
                f"""SELECT permission,note,record_time FROM "user_id_{self.fname}" WHERE user_id=$1"""
            )
            if res := await stmt.fetchrow(user_id):
                return tuple(res)

        return self._default_user_id_full()

    @_handle_exception(create_table_user_id, list)
    async def get_user_id_list(
        self,
        lower_permission: int = 0,
        upper_permission: int = 50,
        *,
        limit: int = 1,
        offset: int = 0,
    ) -> list[int]:
        """
        获取表user_id_{fname}中user_id的列表

        Args:
            lower_permission (int, optional): 获取所有权限级别大于等于lower_permission的user_id. Defaults to 0.
            upper_permission (int, optional): 获取所有权限级别小于等于upper_permission的user_id. Defaults to 50.
            limit (int, optional): 返回数量限制. Defaults to 1.
            offset (int, optional): 偏移. Defaults to 0.

        Returns:
            list[int]: user_id列表
        """

        async with self._pool.acquire() as conn:
            stmt = await conn.prepare(
                f"""SELECT user_id FROM "user_id_{self.fname}" WHERE permission>={lower_permission} AND permission<={upper_permission} ORDER BY record_time DESC LIMIT {limit} OFFSET {offset}""",
            )
            records = await stmt.fetch()

        res = [record['user_id'] for record in records]
        return res

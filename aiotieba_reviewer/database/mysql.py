import datetime
import ssl
from typing import Any, Callable, Final, List, Tuple

import asyncmy
from aiotieba import get_logger as LOG

from ..config import DB_CONFIG


def exec_handler_MySQL(create_table_func: Callable, default_ret: Any):
    """
    处理MySQL异常

    Args:
        create_table_func (Callable): 在无法连接数据库(2003)或表不存在时(1146)执行自动建表
        default_ret (Any): 出现错误时的默认返回值
    """

    def decorator(func):
        async def wrapper(self: "MySQLDB", *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except asyncmy.errors.Error as err:
                try:
                    code = err.args[0]
                    if code in [2003, 1049]:
                        LOG().warning("无法连接数据库 将尝试自动建库")
                        await self.create_database()
                        await create_table_func(self)
                    elif code == 1146:
                        LOG().warning("表不存在 将尝试自动建表")
                        await create_table_func(self)
                except Exception:
                    pass
            return default_ret

        return wrapper

    return decorator


class MySQLDB(object):
    """
    MySQL交互

    Args:
        fname (str): 操作的目标贴吧名. Defaults to ''.

    Attributes:
        fname (str): 操作的目标贴吧名

    Note:
        容器特点: 读多写少 允许外部访问 数据安全性好
        一般用于数据持久化
    """

    __slots__ = ['fname', '_pool']

    _default_port: Final[int] = 3306
    _default_db_name: Final[str] = 'aiotieba'
    _default_minsize: Final[int] = 0
    _default_maxsize: Final[int] = 12
    _default_pool_recycle: Final[int] = 28800

    def __init__(self, fname: str = '') -> None:
        self.fname = fname
        self._pool: asyncmy.Pool = None

    async def __aenter__(self) -> "MySQLDB":
        await self._create_pool()
        return self

    async def __aexit__(self, exc_type=None, exc_val=None, exc_tb=None) -> None:
        if self._pool is not None:
            self._pool.close()
            await self._pool.wait_closed()

    async def _create_pool(self) -> None:
        """
        创建连接池
        """

        ssl_ctx = None
        if cafile := DB_CONFIG.get('ssl_cafile'):
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_ctx.load_verify_locations(cafile=cafile)

        self._pool: asyncmy.Pool = await asyncmy.create_pool(
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            db=DB_CONFIG.get('db', self._default_db_name),
            minsize=DB_CONFIG.get('minsize', self._default_minsize),
            maxsize=DB_CONFIG.get('maxsize', self._default_maxsize),
            pool_recycle=DB_CONFIG.get('pool_recycle', self._default_pool_recycle),
            autocommit=True,
            host=DB_CONFIG.get('host', 'localhost'),
            port=DB_CONFIG.get('port', self._default_port),
            unix_socket=DB_CONFIG.get('unix_socket'),
            ssl=ssl_ctx,
        )

    async def create_database(self) -> bool:
        """
        创建并初始化数据库

        Returns:
            bool: 操作是否成功
        """

        try:
            conn: asyncmy.Connection = await asyncmy.connect(
                host=DB_CONFIG.get('host', 'localhost'),
                port=DB_CONFIG.get('port', self._default_port),
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                unix_socket=DB_CONFIG.get('unix_socket'),
                autocommit=True,
                ssl=self._pool._conn_kwargs['ssl'],
            )

            async with conn.cursor() as cursor:
                db_name = DB_CONFIG.get('db', self._default_db_name)
                await cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")

            await self._create_pool()
            await conn.ensure_closed()

        except asyncmy.errors.Error as err:
            LOG().warning(f"{err}. 请检查配置文件中的`Database`字段是否填写正确")
            return False

        LOG().info(f"成功创建并初始化数据库. db_name={db_name}")
        return True

    async def _create_table_user_id(self) -> None:
        """
        创建表user_id_{fname}
        """

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"CREATE TABLE IF NOT EXISTS `user_id_{self.fname}` \
                    (`user_id` BIGINT PRIMARY KEY, `permission` TINYINT NOT NULL DEFAULT 0, `note` VARCHAR(64) NOT NULL DEFAULT '', `record_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP, \
                    INDEX `permission`(permission), INDEX `record_time`(record_time))"
                )
                LOG().info(f"成功创建表user_id_{self.fname}")

    @exec_handler_MySQL(_create_table_user_id, False)
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
            return False

        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        f"REPLACE INTO `user_id_{self.fname}` VALUES ({user_id},{permission},'{note}',DEFAULT)"
                    )

                    LOG().info(f"Succeeded. forum={self.fname} user_id={user_id} permission={permission}")
                    return True

        except asyncmy.errors.Error as err:
            LOG().warning(f"{err}. forum={self.fname} user_id={user_id}")
            raise

    @exec_handler_MySQL(_create_table_user_id, False)
    async def del_user_id(self, user_id: int) -> bool:
        """
        从表user_id_{fname}中删除user_id

        Args:
            user_id (int): 用户的user_id

        Returns:
            bool: True成功 False失败
        """

        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"DELETE FROM `user_id_{self.fname}` WHERE `user_id`={user_id}")

                    LOG().info(f"Succeeded. forum={self.fname} user_id={user_id}")
                    return True

        except asyncmy.errors.Error as err:
            LOG().warning(f"{err}. forum={self.fname} user_id={user_id}")
            raise

    @exec_handler_MySQL(_create_table_user_id, 0)
    async def get_user_id(self, user_id: int) -> int:
        """
        获取表user_id_{fname}中user_id的权限级别

        Args:
            user_id (int): 用户的user_id

        Returns:
            int: 权限级别
        """

        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"SELECT `permission` FROM `user_id_{self.fname}` WHERE `user_id`={user_id}")

                    if res_tuple := await cursor.fetchone():
                        return res_tuple[0]
                    return 0

        except asyncmy.errors.Error as err:
            LOG().warning(f"{err}. forum={self.fname} user_id={user_id}")
            raise

    @exec_handler_MySQL(_create_table_user_id, (0, '', datetime.datetime(1970, 1, 1)))
    async def get_user_id_full(self, user_id: int) -> Tuple[int, str, datetime.datetime]:
        """
        获取表user_id_{fname}中user_id的完整信息

        Args:
            user_id (int): 用户的user_id

        Returns:
            tuple[int, str, datetime.datetime]: 权限级别, 备注, 记录时间
        """

        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        f"SELECT `permission`,`note`,`record_time` FROM `user_id_{self.fname}` WHERE `user_id`={user_id}"
                    )
                    if res_tuple := await cursor.fetchone():
                        return res_tuple
                    return 0, '', datetime.datetime(1970, 1, 1)

        except asyncmy.errors.Error as err:
            LOG().warning(f"{err}. forum={self.fname} user_id={user_id}")
            raise

    @exec_handler_MySQL(_create_table_user_id, [])
    async def get_user_id_list(
        self, lower_permission: int = 0, upper_permission: int = 5, *, limit: int = 1, offset: int = 0
    ) -> List[int]:
        """
        获取表user_id_{fname}中user_id的列表

        Args:
            lower_permission (int, optional): 获取所有权限级别大于等于lower_permission的user_id. Defaults to 0.
            upper_permission (int, optional): 获取所有权限级别小于等于upper_permission的user_id. Defaults to 5.
            limit (int, optional): 返回数量限制. Defaults to 1.
            offset (int, optional): 偏移. Defaults to 0.

        Returns:
            list[int]: user_id列表
        """

        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        f"SELECT `user_id` FROM `user_id_{self.fname}` WHERE `permission`>={lower_permission} AND `permission`<={upper_permission} ORDER BY `record_time` DESC LIMIT {limit} OFFSET {offset}"
                    )

                    res_tuples = await cursor.fetchall()
                    res_list = [res_tuple[0] for res_tuple in res_tuples]
                    return res_list

        except asyncmy.errors.Error as err:
            LOG().warning(f"{err}. forum={self.fname}")
            raise

    async def _create_table_imghash(self) -> None:
        """
        创建表imghash_{fname}
        """

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"CREATE TABLE IF NOT EXISTS `imghash_{self.fname}` \
                    (`img_hash` BIGINT UNSIGNED PRIMARY KEY, `raw_hash` CHAR(40) UNIQUE NOT NULL, `permission` TINYINT NOT NULL DEFAULT 0, `note` VARCHAR(64) NOT NULL DEFAULT '', `record_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP, \
                    INDEX `permission`(permission), INDEX `record_time`(record_time))"
                )
                LOG().info(f"成功创建表imghash_{self.fname}")

    @exec_handler_MySQL(_create_table_imghash, False)
    async def add_imghash(self, img_hash: int, raw_hash: str, /, permission: int = 0, *, note: str = '') -> bool:
        """
        将img_hash添加到表imghash_{fname}

        Args:
            img_hash (int): 图像的ahash
            raw_hash (str): 贴吧图床hash
            permission (int, optional): 封锁级别. Defaults to 0.
            note (str, optional): 备注. Defaults to ''.

        Returns:
            bool: True成功 False失败
        """

        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        f"REPLACE INTO `imghash_{self.fname}` VALUES ({img_hash},'{raw_hash}',{permission},'{note}',DEFAULT)"
                    )

                    LOG().info(f"Succeeded. forum={self.fname} img_hash={img_hash} permission={permission}")
                    return True

        except asyncmy.errors.Error as err:
            LOG().warning(f"{err}. forum={self.fname} img_hash={img_hash}")
            raise

    @exec_handler_MySQL(_create_table_imghash, False)
    async def del_imghash(self, img_hash: int, *, hamming_dist: int = 0) -> bool:
        """
        从表imghash_{fname}中删除img_hash

        Args:
            img_hash (int): 图像的ahash
            hamming_dist (int): 匹配的最大海明距离 默认为0 即要求图像ahash完全一致

        Returns:
            bool: True成功 False失败
        """

        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    if hamming_dist > 0:
                        await cursor.execute(
                            f"DELETE FROM `imghash_{self.fname}` WHERE BIT_COUNT(`img_hash`^{img_hash})<={hamming_dist}"
                        )
                    else:
                        await cursor.execute(f"DELETE FROM `imghash_{self.fname}` WHERE `img_hash`={img_hash}")

                    LOG().info(f"Succeeded. forum={self.fname} img_hash={img_hash}")
                    return True

        except asyncmy.errors.Error as err:
            LOG().warning(f"{err}. forum={self.fname} img_hash={img_hash}")
            raise

    @exec_handler_MySQL(_create_table_imghash, 0)
    async def get_imghash(self, img_hash: int, *, hamming_dist: int = 0) -> int:
        """
        获取表imghash_{fname}中img_hash的封锁级别

        Args:
            img_hash (int): 图像的ahash
            hamming_dist (int): 匹配的最大海明距离 默认为0 即要求图像ahash完全一致

        Returns:
            int: 封锁级别
        """

        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    if hamming_dist > 0:
                        await cursor.execute(
                            f"SELECT `permission`,BIT_COUNT(`img_hash`^{img_hash}) AS hd FROM `imghash_{self.fname}` HAVING hd<={hamming_dist} ORDER BY hd ASC LIMIT 1"
                        )
                    else:
                        await cursor.execute(
                            f"SELECT `permission` FROM `imghash_{self.fname}` WHERE `img_hash`={img_hash}"
                        )

                    if res_tuple := await cursor.fetchone():
                        return res_tuple[0]
                    return 0

        except asyncmy.errors.Error as err:
            LOG().warning(f"{err}. forum={self.fname} img_hash={img_hash}")
            raise

    @exec_handler_MySQL(_create_table_imghash, (0, ''))
    async def get_imghash_full(self, img_hash: int, *, hamming_dist: int = 0) -> Tuple[int, str]:
        """
        获取表imghash_{fname}中img_hash的完整信息

        Args:
            img_hash (int): 图像的ahash
            hamming_dist (int): 匹配的最大海明距离 默认为0 即要求图像ahash完全一致

        Returns:
            tuple[int, str]: 封锁级别, 备注
        """

        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    if hamming_dist > 0:
                        await cursor.execute(
                            f"SELECT `permission`,`note`,BIT_COUNT(`img_hash`^{img_hash}) AS hd FROM `imghash_{self.fname}` HAVING hd<={hamming_dist} ORDER BY hd ASC LIMIT 1"
                        )
                    else:
                        await cursor.execute(
                            f"SELECT `permission`,`note` FROM `imghash_{self.fname}` WHERE `img_hash`={img_hash}"
                        )

                    if res_tuple := await cursor.fetchone():
                        return res_tuple[:2]
                    return 0, ''

        except asyncmy.errors.Error as err:
            LOG().warning(f"{err}. forum={self.fname} img_hash={img_hash}")
            raise

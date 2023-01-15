from typing import AsyncGenerator

import aiotieba

_fname = ''

client_generator: AsyncGenerator[aiotieba.Client, None] = None
db_generator: AsyncGenerator[aiotieba.MySQLDB, None] = None
db_sqlite_generator: AsyncGenerator[aiotieba.SQLiteDB, None] = None


def set_BDUSS_key(BDUSS_key: str) -> None:
    """
    设置用于吧管理的BDUSS_key

    Args:
        BDUSS_key (str)
    """

    async def _client_generator():
        async with aiotieba.Client(BDUSS_key) as client:
            while 1:
                yield client

    global client_generator
    client_generator = _client_generator


async def get_client() -> aiotieba.Client:
    """
    获取一个客户端

    Returns:
        aiotieba.Client
    """

    return await client_generator.__anext__()


def set_fname(fname: str) -> None:
    """
    设置待管理吧的吧名

    Args:
        fname (str)
    """

    global _fname
    _fname = fname

    async def _db_generator():
        async with aiotieba.MySQLDB(fname) as db:
            while 1:
                yield db

    global db_generator
    db_generator = _db_generator

    async def _db_sqlite_generator():
        async with aiotieba.SQLiteDB(fname) as db_sqlite:
            while 1:
                yield db_sqlite

    global db_sqlite_generator
    db_sqlite_generator = _db_sqlite_generator


def get_fname() -> str:
    return _fname


async def get_db() -> aiotieba.MySQLDB:
    """
    获取一个MySQL客户端

    Returns:
        aiotieba.MySQLDB
    """

    return await db_generator.__anext__()


async def get_db_sqlite() -> aiotieba.SQLiteDB:
    """
    获取一个SQLite客户端

    Returns:
        aiotieba.SQLiteDB
    """

    return await db_sqlite_generator.__anext__()

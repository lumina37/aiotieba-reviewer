from collections.abc import AsyncGenerator

import aiotieba as tb

from .config import get_account
from .database import PostgreDB, SQLiteDB

_fname = ''
_db_sqlite = None

client_generator: AsyncGenerator[tb.Client, None] = None
db_generator: AsyncGenerator[PostgreDB, None] = None


def set_BDUSS_key(BDUSS_key: str) -> None:
    """
    设置用于吧管理的BDUSS_key

    Args:
        BDUSS_key (str)
    """

    async def _client_generator():
        account = get_account(BDUSS_key)
        async with tb.Client(account=account, try_ws=True) as client:
            while 1:
                yield client

    global client_generator
    client_generator = _client_generator()


async def get_client() -> tb.Client:
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
        async with PostgreDB(fname) as db:
            while 1:
                yield db

    global db_generator
    db_generator = _db_generator()

    global _db_sqlite
    _db_sqlite = SQLiteDB(fname)


def get_fname() -> str:
    return _fname


async def get_db() -> PostgreDB:
    """
    获取一个PostgreSQL客户端

    Returns:
        PostgreDB
    """

    return await db_generator.__anext__()


def get_db_sqlite() -> SQLiteDB:
    """
    获取一个SQLite客户端

    Returns:
        SQLiteDB
    """

    return _db_sqlite

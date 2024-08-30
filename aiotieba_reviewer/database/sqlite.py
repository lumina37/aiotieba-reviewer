from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aiotieba import get_logger


def handle_exception(
    null_factory: Callable[[], Any],
    ok_log_level: int = logging.NOTSET,
    err_log_level: int = logging.WARNING,
):
    """
    处理request抛出的异常 只能用于装饰类成员函数

    Args:
        null_factory (Callable[[], Any]): 空构造工厂 用于返回一个默认值
        ok_log_level (int, optional): 正常日志等级. Defaults to logging.NOTSET.
        err_log_level (int, optional): 异常日志等级. Defaults to logging.WARNING.
    """

    def wrapper(func):
        def inner(self, *args, **kwargs):
            def _log(log_level: int, err: Exception | None = None) -> None:
                logger = get_logger()
                if logger.isEnabledFor(err_log_level):
                    if err is None:
                        err = "Suceeded"
                    log_str = f"{err}. args={args} kwargs={kwargs}"
                    record = logger.makeRecord(logger.name, log_level, None, 0, log_str, None, None, func.__name__)
                    logger.handle(record)

            try:
                ret = func(self, *args, **kwargs)

                if ok_log_level:
                    _log(ok_log_level)

            except Exception as err:
                _log(err_log_level, err)

                ret = null_factory()
                ret.err = err

                return ret

            else:
                return ret

        return inner

    return wrapper


class SQLiteDB:
    """
    SQLite交互

    Args:
        fname (str): 操作的目标贴吧名. Defaults to ''.

    Attributes:
        fname (str): 操作的目标贴吧名

    Note:
        容器特点: 读多写多 不允许外部访问 数据安全性差
        一般用于快速缓存
    """

    __slots__ = ['fname', '_conn']

    def __init__(self, fname: str = '') -> None:
        self.fname = fname
        db_path = Path(f".cache/{self.fname}.sqlite")
        need_init = False

        if not db_path.exists():
            need_init = True
            db_path.parent.mkdir(0o755, exist_ok=True)

        self._conn = sqlite3.connect(str(db_path), timeout=15.0, isolation_level=None, cached_statements=64)
        self._conn.execute("PRAGMA journal_mode=OFF")
        self._conn.execute("PRAGMA synchronous=OFF")
        if need_init:
            self.create_table_id()

    def close(self) -> None:
        self._conn.close()

    def create_table_id(self) -> None:
        """
        创建表id_{fname}
        """

        self._conn.execute(
            f"CREATE TABLE IF NOT EXISTS `id_{self.fname}` \
            (`id` INTEGER PRIMARY KEY, `tag` INTEGER NOT NULL, `record_time` INTEGER NOT NULL DEFAULT CURRENT_TIMESTAMP)",
        )

    @handle_exception(bool)
    def add_id(self, id_: int, *, tag: int = 0) -> bool:
        """
        将id添加到表id_{fname}

        Args:
            id_ (int): tid或pid
            tag (int, optional): 自定义标签. Defaults to 0.

        Returns:
            bool: True成功 False失败
        """

        self._conn.execute(f"REPLACE INTO `id_{self.fname}` VALUES ({id_},{tag},NULL)")
        return True

    @handle_exception(bool, ok_log_level=logging.INFO)
    def del_id(self, _id: int) -> bool:
        """
        从表id_{fname}中删除id

        Args:
            _id (int): tid或pid

        Returns:
            bool: True成功 False失败
        """

        self._conn.execute(f"DELETE FROM `id_{self.fname}` WHERE `id`={_id}")
        return True

    @handle_exception(lambda: None)
    def get_id(self, id_: int) -> int | None:
        """
        获取表id_{fname}中id对应的tag值

        Args:
            id_ (int): tid或pid

        Returns:
            int | None: 自定义标签 None表示表中无id
        """

        cursor = self._conn.execute(f"SELECT `tag` FROM `id_{self.fname}` WHERE `id`={id_}")
        if res_tuple := cursor.fetchone():
            return res_tuple[0]
        return None

    @handle_exception(bool, ok_log_level=logging.INFO)
    def truncate(self, day: int) -> bool:
        """
        删除表id_{fname}中day天前的陈旧记录

        Args:
            day (int)

        Returns:
            bool: True成功 False失败
        """

        self._conn.execute(f"DELETE FROM `id_{self.fname}` WHERE `record_time` < datetime('now','-{day} day')")
        self._conn.execute("VACUUM")
        return True

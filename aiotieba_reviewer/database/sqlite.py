import sqlite3
from pathlib import Path
from typing import Optional

from aiotieba import get_logger as LOG


class SQLiteDB(object):
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
            self._create_table_id()

    def close(self) -> None:
        self._conn.close()

    def _create_table_id(self) -> None:
        """
        创建表id_{fname}
        """

        self._conn.execute(
            f"CREATE TABLE IF NOT EXISTS `id_{self.fname}` \
            (`id` INTEGER PRIMARY KEY, `tag` INTEGER NOT NULL, `record_time` INTEGER NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )

    def add_id(self, _id: int, *, tag: int = 0) -> bool:
        """
        将id添加到表id_{fname}

        Args:
            _id (int): tid或pid
            tag (int, optional): 自定义标签. Defaults to 0.

        Returns:
            bool: True成功 False失败
        """

        try:
            self._conn.execute(f"REPLACE INTO `id_{self.fname}` VALUES ({_id},{tag},NULL)")
        except sqlite3.Error as err:
            LOG().warning(f"{err}. forum={self.fname} id={_id}")
            return False
        return True

    def get_id(self, _id: int) -> Optional[int]:
        """
        获取表id_{fname}中id对应的tag值

        Args:
            _id (int): tid或pid

        Returns:
            int | None: 自定义标签 None表示表中无id
        """

        try:
            cursor = self._conn.execute(f"SELECT `tag` FROM `id_{self.fname}` WHERE `id`={_id}")
        except sqlite3.Error as err:
            LOG().warning(f"{err}. forum={self.fname} id={_id}")
            return False
        else:
            if res_tuple := cursor.fetchone():
                return res_tuple[0]
            return None

    def del_id(self, _id: int) -> bool:
        """
        从表id_{fname}中删除id

        Args:
            _id (int): tid或pid

        Returns:
            bool: True成功 False失败
        """

        try:
            self._conn.execute(f"DELETE FROM `id_{self.fname}` WHERE `id`={_id}")
        except sqlite3.Error as err:
            LOG().warning(f"{err}. forum={self.fname} id={_id}")
            return False

        LOG().info(f"Succeeded. forum={self.fname} id={_id}")
        return True

    def truncate(self, day: int) -> bool:
        """
        删除表id_{fname}中day天前的陈旧记录

        Args:
            day (int)

        Returns:
            bool: True成功 False失败
        """

        try:
            self._conn.execute(f"DELETE FROM `id_{self.fname}` WHERE `record_time` < datetime('now','-{day} day')")
            self._conn.execute("VACUUM")
        except sqlite3.Error as err:
            LOG().warning(f"{err}. forum={self.fname}")
            return False

        LOG().info(f"Succeeded. forum={self.fname} day={day}")
        return True

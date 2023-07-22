import sys

from .enums import Ops
from .typing import TypeObj


class Punish(object):
    """
    处罚操作

    Attributes:
        op (Ops, optional): 删除类型. Defaults to Ops.NORMAL.
        days (int, optional): 封禁天数. Defaults to 0.
        note (str, optional): 处罚理由. Defaults to ''.
    """

    __slots__ = [
        'obj',
        'line',
        'op',
        'day',
        '_note',
        '_raw_note',
    ]

    def __init__(self, obj: TypeObj, op: Ops = Ops.NORMAL, day: int = 0, note: str = ''):
        self.obj = obj
        self.op = op
        self.day = day
        self._note = None
        if op > Ops.NORMAL:
            self.line = sys._getframe(1).f_lineno
            self._raw_note = note
        else:
            self.line = 0
            self._raw_note = ''

    def __bool__(self) -> bool:
        if self.op > Ops.NORMAL:
            return True
        if self.day:
            return True
        return False

    def __repr__(self) -> str:
        return str(
            {
                'op': self.op,
                'day': self.day,
                'note': self.note,
            }
        )

    def __or__(self, rhs: "Punish") -> "Punish":
        if rhs.day > self.day:
            return rhs
        if rhs.op > self.op:
            return rhs
        return self

    @property
    def note(self) -> str:
        if self._note is None:
            self._note = f"L{self.line} {self._raw_note}"
        return self._note

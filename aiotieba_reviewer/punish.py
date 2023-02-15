import sys

from ._typing import TypeObj
from .enums import Ops


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
        'op',
        'day',
        'trace',
        'note',
    ]

    def __init__(self, obj: TypeObj, op: Ops = Ops.NORMAL, day: int = 0, note: str = ''):
        self.obj = obj
        self.op = op
        self.day = day
        if op > Ops.NORMAL:
            line = sys._getframe(1).f_lineno
            self.note = f"L{line} {note}"
        else:
            self.note = note

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

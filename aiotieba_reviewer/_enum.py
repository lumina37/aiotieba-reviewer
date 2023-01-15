import enum


class Ops(enum.IntEnum):
    """
    待执行的操作类型

    各比特位从高到低意义分别为
    [是否作用于祖父级] [是否作用于父级] [是否删除] [是否屏蔽] [是否白名单]

    如 0b00000意为一切正常 0b01100意为删除父级
    """

    NORMAL = 0
    WHITE = 1
    HIDE = 2
    DELETE = 4
    PARENT = 8
    GRANDPARENT = 16

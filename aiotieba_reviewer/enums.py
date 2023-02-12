import enum


class Ops(enum.IntEnum):
    """
    待执行的操作类型

    各比特位从高到低意义分别为
    [是否作用于祖父级] [是否作用于父级] [是否删除] [是否屏蔽] [是否打印debug信息]

    如 0b00000意为一切正常 0b01100意为删除父级

    一般来说数字越大效力越猛
    """

    NORMAL = 0
    DEBUG = 1
    HIDE = 2
    DELETE = 4
    PARENT = 8
    GRANDPARENT = 16

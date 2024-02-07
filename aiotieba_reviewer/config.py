import sys

import aiotieba as tb

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

try:
    with open("account.toml", "rb") as f:
        ACC_CONFIG = tomllib.load(f)
except FileNotFoundError:
    ACC_CONFIG = {}

try:
    with open("database.toml", "rb") as f:
        DB_CONFIG = tomllib.load(f)
except FileNotFoundError:
    DB_CONFIG = {}


def get_account(BDUSS_key: str) -> tb.Account:
    """
    通过BDUSS_key获取Account实例

    Args:
        BDUSS_key (str): BDUSS_key

    Returns:
        Account: Account实例
    """

    account_dic = ACC_CONFIG[BDUSS_key]
    account = tb.Account.from_dict(account_dic)
    return account

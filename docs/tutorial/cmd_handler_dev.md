# 指令管理器配置教程

## 配置文件

在当前工作目录下新建配置文件`account.toml`，并参考下列案例填写你自己的配置

```toml
[my_account_0]
BDUSS = "账号0的BDUSS"

[my_account_1]
BDUSS = "账号1的BDUSS"

[my_account_2]
BDUSS = "账号2的BDUSS"
```

在当前工作目录下新建配置文件`database.toml`，并参考下列案例填写你自己的配置

```toml
host = "127.0.0.1"
port = 3306
user = ""                                 # 填用户名
password = ""                             # 填密码
db = "aiotieba"                           # 使用的数据库名，不填则默认为aiotieba
unix_socket = "/var/lib/mysql/mysql.sock" # 用于优化linux系统的本机连接速度，看不懂就不用填
pool_recycle = 3600                       # 填连接超时的秒数，需要与服务端保持一致，不填则默认为28800秒
ssl_cafile = "/path/to/your/cacert.file"  # 用于加密连接的CA证书的路径
```

在当前工作目录下新建配置文件`cmd_handler.toml`，并参考下列案例填写你自己的配置

```toml
listener = "my_account_1"  # 在这里填用于监听at信息的账号的BDUSS_key

[[Forum]]
fname = "lol半价"  # 在这里填贴吧名
key = "my_account_0"  # 在这里填用于在该吧行使吧务权限的账号的BDUSS_key

[[Forum]]
fname = "抗压背锅"  # 在这里填另一个贴吧名
key = "my_account_1"  # 在这里填用于在该吧行使吧务权限的账号的BDUSS_key
```

## 运行脚本

将`examples/cmd_handler.py`复制到当前工作目录下

```shell
mv examples/cmd_handler.py .
```

运行`cmd_handler.py`（对`Windows`平台，建议使用`pythonw.exe`无窗口运行，对`Linux`平台，建议使用如下的`nohup`指令在后台运行）

```shell
nohup python -OO cmd_handler.py >/dev/null 2>&1 &
```
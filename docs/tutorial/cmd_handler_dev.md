# 指令管理器配置教程

## 配置文件

在当前工作目录下新建配置文件`cmd_handler.toml`，并参考下列案例填写你自己的配置

```toml
listener = "listener"  # 在这里填用于监听at信息的账号的BDUSS_key

[[Forum]]
fname = "lol半价"  # 在这里填贴吧名
admin = "default"  # 在这里填用于在该吧行使吧务权限的账号的BDUSS_key
speaker = "default"  # 在这里填用于在该吧发送回复的账号的BDUSS_key

[[Forum]]
fname = "抗压背锅"  # 在这里填另一个贴吧名
admin = "default"  # 在这里填用于在该吧行使吧务权限的账号的BDUSS_key
speaker = "default"  # 在这里填用于在该吧发送回复的账号的BDUSS_key
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
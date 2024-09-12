# 云审查教程

## 扫描范围

在贴吧服务端不出现故障的理想情况下，默认的扫描设置可以完全覆盖目标贴吧首页的每一条内容

通过适当的配置，审查工具可以检查以上内容中是否存在：

+ **违规图片**

![eg_1](https://user-images.githubusercontent.com/48282276/176145251-35f36f73-2f23-4b1f-a456-9e62f97c40af.png)

+ **违规链接**

![eg_2](https://user-images.githubusercontent.com/48282276/176145401-6b16140c-53cb-4575-9f9a-4b47540bd5a5.png)

+ **违规文字**

![eg_3](https://user-images.githubusercontent.com/48282276/176145434-d8deab64-3ceb-472b-b51d-564246162226.png)

+ **黑名单用户**

![eg_4](https://user-images.githubusercontent.com/48282276/176145443-2021e697-c858-48c3-91b4-fba409ef6e20.png)

## 实战效果

以下是应用于[孙笑川吧](https://tieba.baidu.com/f?ie=utf-8&kw=%E5%AD%99%E7%AC%91%E5%B7%9D)的云审查工具的实战效果。

![backstage](https://user-images.githubusercontent.com/48282276/165777398-47e00f26-a46f-4b7c-a03e-03092e5d31ba.png)

![log](https://user-images.githubusercontent.com/48282276/165776593-ab5feec4-6529-4702-82e5-1904e9e8630f.png)

## 使用方法

1. 首先，你需要一个PostgreSQL数据库，用来缓存通过检测的内容id以及记录用户权限级别（黑、白名单）
1. 参考[**该教程**](cmd_handler_dev.md)，填写`database.toml`字段，以便aiotieba-reviewer使用你的PostgreSQL数据库。在你第一次调用特定方法时会自动创建数据库表，因此你无须手动建表
1. 自定义审查行为：请参照我给出的例子自己编程修改[reviewer_example.py](https://github.com/lumina37/aiotieba-reviewer/blob/develop/examples/reviewer_example.py)
1. 运行`your_reviewer.py`

```shell
python your_reviewer.py --no_test
```

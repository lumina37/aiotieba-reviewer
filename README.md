## 简介

基于[**aiotieba**](https://github.com/Starry-OvO/aiotieba)实现的百度贴吧高弹性吧务审查框架

+ 类型注解全覆盖，方法注释全覆盖，类属性注释全覆盖，内部命名统一
+ 支持获取用户主页信息（包括个性签名、发帖量、吧龄、成长等级、ip归属地、虚拟形象信息...）、历史发帖、关注吧、关注用户、粉丝列表...
+ 支持富文本解析，获取图片信息、at用户id、链接内容、投票帖、转发帖...
+ 支持针对多条相互关联的内容的审查
+ 支持二维码识别、相似图像查找
+ 支持用户黑白名单、图片黑白名单
+ 使用本地缓存避免重复检测，极大提升性能
+ 优先使用websocket接口，节省带宽

## git安装 (更新较快)

### 安装

```shell
git clone https://github.com/Starry-OvO/aiotieba-reviewer.git --depth=1 -b develop
cd ./aiotieba-reviewer
pip install -e .
```

### 更新

```shell
git pull
```

## pip安装 (更新较慢)

### 安装

```shell
pip install aiotieba-reviewer
```

### 更新

```shell
pip install -U aiotieba-reviewer
```

## 教程

[**云审查教程**](https://review.aiotieba.cc/tutorial/reviewer/)

## 客户名单

*2023.07.06更新*

|      吧名      | 关注用户数 | 最近24天日均访问量 | 日均主题帖数 | 日均回复数 |
| :------------: | :--------: | :----------------: | :----------: | :--------: |
|    抗压背锅    | 5,115,635  |     1,493,512      |    3,055     |   87,929   |
|     孙笑川     | 4,275,937  |      640,641       |    4,799     |  183,930   |
|    原神内鬼    |  608,257   |      414,256       |     742      |   28,460   |
|      憨批      |   29,659   |      148,107       |    3,768     |   60,921   |
|    lol半价     | 2,088,777  |       73,032       |     259      |   20,829   |
|     vtuber     |  226,211   |       12,529       |      70      |    946     |
|    天堂鸡汤    |  367,953   |       11,705       |      88      |   3,107    |
|      嘉然      |   61,291   |       7,332        |      51      |    715     |
|    元气骑士    |  274,821   |       4,178        |      45      |    508     |
| vtuber自由讨论 |   17,271   |        973         |      1       |     19     |

## 友情链接

+ [TiebaManager（吧务管理器 有用户界面）](https://github.com/dog194/TiebaManager)
+ [TiebaLite（第三方安卓客户端）](https://github.com/HuanCheng65/TiebaLite/tree/4.0-dev)
+ [贴吧protobuf定义文件合集](https://github.com/n0099/tbclient.protobuf)

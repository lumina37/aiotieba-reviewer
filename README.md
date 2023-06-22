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

## 安装与更新

### 安装 (git)

```shell
git clone https://github.com/Starry-OvO/aiotieba-reviewer.git --depth=1 -b develop
cd ./aiotieba-reviewer
pip install .
```

### 更新 (git)

```shell
git pull
```

### 安装 (pip)

```shell
pip install aiotieba-reviewer
```

### 更新 (pip)

```shell
pip install -U aiotieba-reviewer
```

## 教程

[**云审查教程**](https://review.aiotieba.cc/tutorial/reviewer/)

## 客户名单

*2023.06.22更新*

|      吧名      | 关注用户数 | 最近24天日均访问量 | 日均主题帖数 | 日均回复数 |
| :------------: | :--------: | :----------------: | :----------: | :--------: |
|    抗压背锅    | 5,083,671  |     1,162,415      |    2,170     |   74,508   |
|     孙笑川     | 4,221,896  |      682,341       |    5,175     |  205,832   |
|    原神内鬼    |  604,673   |      399,755       |     760      |   28,481   |
|      憨批      |   25,323   |      155,123       |    3,985     |   69,364   |
|    lol半价     | 2,088,269  |       70,474       |     226      |   12,115   |
|    天堂鸡汤    |  366,047   |       13,351       |      93      |   3,733    |
|     vtuber     |  225,814   |       12,084       |      72      |    909     |
|      嘉然      |   61,296   |       8,438        |      56      |    832     |
|    元气骑士    |  274,395   |       4,177        |      44      |    479     |
| vtuber自由讨论 |   17,275   |        969         |      1       |     21     |

## 友情链接

+ [TiebaManager（吧务管理器 有用户界面）](https://github.com/dog194/TiebaManager)
+ [TiebaLite（第三方安卓客户端）](https://github.com/HuanCheng65/TiebaLite/tree/4.0-dev)
+ [贴吧protobuf定义文件合集](https://github.com/n0099/tbclient.protobuf)

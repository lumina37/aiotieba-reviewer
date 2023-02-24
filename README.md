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

## 安装 (beta)

```shell
git clone https://github.com/Starry-OvO/aiotieba-reviewer.git
cd ./aiotieba-reviewer
pip install .
```

## 教程

[**云审查教程**](https://review.aiotieba.cc/tutorial/reviewer/)

## 客户名单

*2023.02.24更新*

|      吧名      | 关注用户数 | 最近29天日均访问量 | 日均主题帖数 | 日均回复数 |
| :------------: | :--------: | :----------------: | :----------: | :--------: |
|    抗压背锅    | 4,726,199  |     1,022,854      |    2,050     |   70,140   |
|    原神内鬼    |  557,244   |      743,265       |    1,645     |   59,116   |
|     孙笑川     | 3,412,024  |      616,940       |    5,759     |  191,275   |
|      嘉然      |   59,952   |      222,679       |      89      |   1,320    |
|      乃琳      |   17,362   |      222,586       |      20      |    270     |
|      贝拉      |   21,845   |      222,427       |      30      |    593     |
|      向晚      |   30,803   |      221,129       |      38      |    551     |
|    逆水寒ol    |  793,924   |      169,196       |     893      |   17,928   |
|    lol半价     | 2,023,104  |      152,976       |    2,990     |  108,882   |
|    新孙笑川    |  582,371   |       33,358       |     330      |   11,415   |
|      宫漫      | 1,525,373  |       31,494       |     123      |   1,895    |
|     vtuber     |  222,752   |       19,679       |      95      |   1,344    |
| vtuber自由讨论 |   17,285   |       1,417        |      2       |     37     |

## 友情链接

+ [TiebaManager（吧务管理器 有用户界面）](https://github.com/dog194/TiebaManager)
+ [TiebaLite（第三方安卓客户端）](https://github.com/HuanCheng65/TiebaLite/tree/4.0-dev)
+ [贴吧protobuf定义文件合集](https://github.com/n0099/tbclient.protobuf)

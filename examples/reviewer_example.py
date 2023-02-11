import argparse
import asyncio
import re
from typing import List, Optional

import aiotieba_reviewer as tbr
from aiotieba_reviewer import Comment, Ops, Post, Punish, TypeObj


@tbr.reviewer.post.set_checker()
async def check_post(post: Post) -> Optional[Punish]:
    punish = await _check_post(post)
    if punish:
        return punish
    punish = await check_text(post)
    if punish:
        return punish


async def _check_post(post: Post) -> Optional[Punish]:

    text = post.text
    if text.count('\n') > 134:
        return Punish(post, Ops.DELETE, note="闪光弹")


@tbr.reviewer.comments.set_producer
async def comments_producer(post: Post) -> List[Comment]:
    return post.comments


@tbr.reviewer.comment.set_checker()
async def check_text(obj: TypeObj) -> Optional[Punish]:

    if obj.user.level >= 7:
        return

    text = obj.text
    if re.search(r"蜘蛛", text):
        return Punish(obj, Ops.DELETE)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no_test",
        help="测试模式默认开启以避免误操作 生产环境下使用该选项将其关闭",
        action="store_true",
    )
    args = parser.parse_args()

    async def main():
        tbr.set_BDUSS_key('...')
        tbr.set_fname('...')

        if args.no_test:
            with tbr.no_test():
                await tbr.run()
        else:
            await tbr.run(90.0)

    asyncio.run(main())

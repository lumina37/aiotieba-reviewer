from typing import Union

from aiotieba.client.get_comments import Comment
from aiotieba.client.get_posts import Post
from aiotieba.client.get_threads import Thread

TypeObj = Union[Thread, Post, Comment]

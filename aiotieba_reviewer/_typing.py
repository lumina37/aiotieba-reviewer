from typing import Union

from aiotieba.api.get_comments import Comment
from aiotieba.api.get_posts import Post
from aiotieba.api.get_threads import Thread

TypeObj = Union[Thread, Post, Comment]

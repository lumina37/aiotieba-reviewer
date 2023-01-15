from typing import Union

from aiotieba.client.get_comments._classdef import Comment
from aiotieba.client.get_posts._classdef import Post
from aiotieba.client.get_threads._classdef import Thread

TypeObj = Union[Thread, Post, Comment]

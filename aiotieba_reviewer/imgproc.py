from typing import Tuple

import cv2 as cv
import numpy as np
from aiotieba import LOG

from .client import get_db

_qrdetector = None
_img_hasher = None


def qrdetector() -> "cv.QRCodeDetector":
    global _qrdetector
    if _qrdetector is None:
        _qrdetector = cv.QRCodeDetector()
    return _qrdetector


def img_hasher() -> "cv.img_hash.AverageHash":
    global _img_hasher
    if _img_hasher is None:
        _img_hasher = cv.img_hash.AverageHash.create()
    return _img_hasher


def decode_QRcode(image: "np.ndarray") -> str:
    """
    解码图像中的二维码

    Args:
        image (np.ndarray): 图像

    Returns:
        str: 二维码信息 解析失败时返回''
    """

    try:
        data = qrdetector().detectAndDecode(image)[0]
    except Exception as err:
        LOG().warning(err)
        data = ''

    return data


def has_QRcode(image: "np.ndarray") -> bool:
    """
    图像是否包含二维码

    Args:
        image (np.ndarray): 图像

    Returns:
        bool: True则包含 False则不包含
    """

    try:
        res = qrdetector().detect(image)[0]
    except Exception as err:
        LOG().warning(err)
        res = False

    return res


def compute_imghash(image: "np.ndarray") -> int:
    """
    计算图像的ahash

    Args:
        image (np.ndarray): 图像

    Returns:
        int: 图像的ahash
    """

    try:
        img_hash_array = img_hasher().compute(image).flatten()
        img_hash = 0
        for hash_num, shift in zip(img_hash_array, range(56, -1, -8)):
            img_hash += int(hash_num) << shift
    except Exception as err:
        LOG().warning(err)
        img_hash = 0

    return img_hash


async def get_imghash(image: "np.ndarray", *, hamming_dist: int = 0) -> int:
    """
    获取图像的封锁级别

    Args:
        image (np.ndarray): 图像
        hamming_dist (int): 匹配的最大海明距离 默认为0 即要求图像phash完全一致

    Returns:
        int: 封锁级别
    """

    if img_hash := compute_imghash(image):
        db = await get_db()
        return await db.get_imghash(img_hash, hamming_dist=hamming_dist)
    return 0


async def get_imghash_full(image: "np.ndarray", *, hamming_dist: int = 0) -> Tuple[int, str]:
    """
    获取图像的完整信息

    Args:
        image (np.ndarray): 图像
        hamming_dist (int): 匹配的最大海明距离 默认为0 即要求图像phash完全一致

    Returns:
        tuple[int, str]: 封锁级别, 备注
    """

    if img_hash := compute_imghash(image):
        db = await get_db()
        return await db.get_imghash_full(img_hash, hamming_dist=hamming_dist)
    return 0, ''

import asyncio
from typing import Generator, Union

from ..client import get_fname
from . import thread


async def loop(time_interval: Union[float, Generator[float, None, None]] = 0.0) -> None:
    while 1:
        await thread.runner._runner(get_fname())
        await asyncio.sleep(time_interval)


async def loop_with_interval_gen(time_interval_gen: Generator[float, None, None]) -> None:
    for time_interval in time_interval_gen:
        await thread.runner._runner(get_fname())
        if time_interval:
            await asyncio.sleep(time_interval)

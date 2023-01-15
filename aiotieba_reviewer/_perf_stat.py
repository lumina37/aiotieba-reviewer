import time
from collections import deque


class perf_stat(object):
    """
    性能统计工具

    Args:
        perf_rec_maxlen (int, optional): 性能记录队列的最大长度. Defaults to 30.
    """

    __slots__ = [
        '_rec_queue',
        '_acc_time_ns',
    ]

    def __init__(self, perf_rec_maxlen: int = 30) -> None:
        self._rec_queue = deque(maxlen=perf_rec_maxlen + 1)
        self._acc_time_ns = 0

    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            start = time.perf_counter_ns()

            res = await func(*args, **kwargs)

            end = time.perf_counter_ns()
            time_cost_ns = end - start
            self._acc_time_ns += time_cost_ns
            self._rec_queue.append(time_cost_ns)

            if len(self._rec_queue) == self._rec_queue.maxlen:
                remove_rec = self._rec_queue.popleft()
                self._acc_time_ns -= remove_rec

            return res

        return wrapper

    @property
    def avg_perf(self) -> float:
        """
        平均耗时

        Note:
            单位为毫秒
        """
        if _len := len(self._rec_queue):
            return self._acc_time_ns / (10e6 * _len)
        else:
            return 0.0

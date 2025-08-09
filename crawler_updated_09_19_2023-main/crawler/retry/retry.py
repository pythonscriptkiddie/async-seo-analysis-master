import asyncio
import logging
from typing import Callable, Awaitable

class TooManyRetries(Exception):
    pass

async def retry(coro: Callable[[], Awaitable],
                max_retries: int,
                timeout: float,
                retry_interval: float):
    '''Retry a task a specified number of times. If we encounter an exception, this coroutine
    will log it and sleep for the retry interval before retrying.'''
    for retry_num in range(0, max_retries):
        try:
            return await asyncio.wait_for(coro(), timeout=timeout)
        except Exception as e:
            logging.exception(f'Exception while waiting (tried {retry_num}) times, retrying',
            exc_info=e) #if we get an exception, log it and sleep for the retry interval
            await asyncio.sleep(retry_interval)
        raise TooManyRetries() #if we've failed too many times, raise an exception to indicate that.
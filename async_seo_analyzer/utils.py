import asyncio
import logging
from typing import Awaitable, Callable
from urllib.parse import urlsplit


class TooManyRetries(Exception):
    pass


async def retry(coro: Callable[[], Awaitable], max_retries: int, timeout: float, retry_interval: float):
    for attempt in range(max_retries):
        try:
            return await asyncio.wait_for(coro(), timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            logging.exception(
                "Exception during retry (attempt %s/%s), sleeping %ss",
                attempt + 1,
                max_retries,
                retry_interval,
                exc_info=exc,
            )
            await asyncio.sleep(retry_interval)
    raise TooManyRetries()


def rel_to_abs_url(link: str, base_domain: str, url: str) -> str:
    if ":" in link:
        return link

    relative_path = link
    base = urlsplit(base_domain)
    domain = base.netloc

    if domain.endswith("/"):
        domain = domain[:-1]

    if len(relative_path) > 0 and relative_path[0] == "?":
        if "?" in url:
            return f"{url[:url.index('?')]}{relative_path}"
        return f"{url}{relative_path}"

    if len(relative_path) > 0 and relative_path[0] != "/":
        relative_path = f"/{relative_path}"

    return f"{base.scheme}://{domain}{relative_path}"
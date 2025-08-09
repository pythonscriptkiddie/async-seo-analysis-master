import asyncio
import logging
from typing import Awaitable, Callable
from urllib.parse import urlsplit


class TooManyRetries(Exception):
    """Exception raised when a retryable operation exhausts all attempts."""


async def retry(coro: Callable[[], Awaitable], max_retries: int, timeout: float, retry_interval: float):
    """Run an async callable with retry, timeout and fixed backoff.

    Parameters
    - coro: Zero-argument async callable to execute.
    - max_retries: Maximum number of attempts before raising TooManyRetries.
    - timeout: Seconds to wait for a single attempt before timing out.
    - retry_interval: Seconds to sleep between attempts after a failure.

    Returns
    - The result of the successful attempt.

    Raises
    - TooManyRetries: If all attempts fail or time out.
    """
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
    """Resolve a possibly-relative link to an absolute URL.

    Handles protocol-relative URLs, query-only links, and relative paths against
    the given base URL.

    Parameters
    - link: The href found in a document.
    - base_domain: A base site URL (protocol + domain) used to construct absolute URLs.
    - url: The full URL of the current page.

    Returns
    - An absolute URL string.
    """
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
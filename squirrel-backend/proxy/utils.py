import asyncio
import logging
from typing import Dict, AsyncGenerator
import httpx

logger = logging.getLogger(__name__)


async def stream_with_retry(url: str, headers: Dict[str, str], chunk_size: int = 1024 * 512, max_retries: int = 3) -> \
        AsyncGenerator[bytes, None]:
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                async with client.stream("GET", url, headers=headers) as resp:
                    resp.raise_for_status()
                    async for chunk in resp.aiter_bytes(chunk_size=chunk_size):
                        yield chunk
            return
        except (httpx.NetworkError, httpx.TimeoutException, httpx.StreamClosed) as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                raise
            logger.warning(f"Attempt {attempt + 1} failed, retrying: {str(e)}")
            await asyncio.sleep(1)

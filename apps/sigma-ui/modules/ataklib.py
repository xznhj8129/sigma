import asyncio
from typing import Tuple


async def start_atak_service() -> Tuple[asyncio.Queue, asyncio.Queue]:
    """
    Start a placeholder ATAK service.

    Returns inbound/outbound queues for future integrations.
    """
    in_queue: asyncio.Queue = asyncio.Queue()
    out_queue: asyncio.Queue = asyncio.Queue()

    async def _ticker():
        while True:
            await asyncio.sleep(3600)

    asyncio.create_task(_ticker())
    return in_queue, out_queue

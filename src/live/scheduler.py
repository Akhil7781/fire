"""Stage 8.42 Background Polling Scheduler.

Executes periodic near-real-time NASA FIRMS polling every 10 minutes.
Catches all network and processing exceptions to guarantee continuous uptime.
"""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Optional, Dict, Any

from src.live.firms_poller import FirmsNrtPoller, FirmsPollerError
from src.live.event_processor import LiveEventProcessor
from src.live.live_state import LiveStateTracker, get_live_state

logger = logging.getLogger(__name__)

class LiveScheduler:
    """Async background task scheduler for FIRMS NRT monitoring."""

    def __init__(
        self,
        interval_seconds: int = 600,  # 10 minutes (Requirement C)
        poller: Optional[FirmsNrtPoller] = None,
        processor: Optional[LiveEventProcessor] = None,
        state: Optional[LiveStateTracker] = None
    ):
        self.interval_seconds = interval_seconds
        self.poller = poller or FirmsNrtPoller()
        self.processor = processor or LiveEventProcessor()
        self.state = state or get_live_state()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._poll_lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    async def poll_once(self, days: int = 1) -> Dict[str, Any]:
        """Executes a single end-to-end FIRMS polling and attribution cycle."""
        async with self._poll_lock:
            self.state.record_poll_start()
            t0 = time.perf_counter()

            try:
                # 1. Download from NASA FIRMS (in thread pool to avoid blocking async event loop)
                t_dl_start = time.perf_counter()
                loop = asyncio.get_running_loop()
                raw_detections = await loop.run_in_executor(
                    None, self.poller.fetch_detections, days
                )
                download_time_s = time.perf_counter() - t_dl_start

                # 2. Process detections: deduplicate -> cluster -> infer -> GIS -> DB
                result = await loop.run_in_executor(
                    None, self.processor.process_live_detections, raw_detections, download_time_s
                )
                return result

            except FirmsPollerError as fe:
                err_msg = f"FIRMS Poll Error: {str(fe)}"
                logger.warning(err_msg)
                self.state.record_poll_failure(err_msg, degraded=True)
                return {"status": "ERROR", "error": err_msg}

            except Exception as e:
                err_msg = f"Unexpected error during live poll: {str(e)}"
                logger.error(err_msg, exc_info=True)
                self.state.record_poll_failure(err_msg, degraded=True)
                return {"status": "ERROR", "error": err_msg}

    async def _run_loop(self):
        """Continuous polling background loop."""
        logger.info(f"LiveScheduler started. Polling every {self.interval_seconds}s (10 min).")
        # Run initial poll immediately
        await self.poll_once()

        while self._running:
            try:
                await asyncio.sleep(self.interval_seconds)
                if not self._running:
                    break
                await self.poll_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in LiveScheduler loop: {e}", exc_info=True)
                await asyncio.sleep(10)

        logger.info("LiveScheduler background loop terminated.")

    def start(self):
        """Starts background polling task."""
        if self._running:
            return
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._run_loop())
        except RuntimeError:
            logger.info("No running asyncio event loop; scheduler running flag enabled.")

    def stop(self):
        """Stops background polling task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("LiveScheduler stopped.")

_GLOBAL_SCHEDULER: Optional[LiveScheduler] = None

def get_scheduler() -> LiveScheduler:
    global _GLOBAL_SCHEDULER
    if _GLOBAL_SCHEDULER is None:
        _GLOBAL_SCHEDULER = LiveScheduler()
    return _GLOBAL_SCHEDULER

"""Stage 8.42 Live Near-Real-Time (NRT) Package.

Provides automated polling, deduplication, event clustering, neural attribution,
and GIS proximity enrichment.
"""

from src.live.firms_poller import FirmsNrtPoller, FirmsPollerError
from src.live.event_processor import LiveEventProcessor
from src.live.scheduler import LiveScheduler, get_scheduler
from src.live.live_state import LiveStateTracker, get_live_state

__all__ = [
    "FirmsNrtPoller",
    "FirmsPollerError",
    "LiveEventProcessor",
    "LiveScheduler",
    "get_scheduler",
    "LiveStateTracker",
    "get_live_state"
]

import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from api.market_service import is_trading_session, refresh_and_persist
from api.orchestrator import LLMConfigurationError, LLMProviderError, auto_analysis_enabled, auto_analysis_interval_minutes, run_cross_market_analysis

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
_last_auto_analysis_at = 0.0


def collect_market_snapshot() -> None:
    if not is_trading_session():
        logger.info("Outside trading session; skipping market collection")
        return
    snapshot = refresh_and_persist()
    logger.info("Stored %s snapshot with %d movers", snapshot["source"], len(snapshot["movers"]))


def coordinate_cross_market() -> None:
    global _last_auto_analysis_at
    if not is_trading_session() or not auto_analysis_enabled():
        return
    interval_seconds = auto_analysis_interval_minutes() * 60
    if time.monotonic() - _last_auto_analysis_at < interval_seconds:
        return
    try:
        run_cross_market_analysis()
        _last_auto_analysis_at = time.monotonic()
        logger.info("Stored latest cross-market model analysis")
    except LLMConfigurationError:
        logger.info("LLM auto-analysis enabled but no provider is configured")
    except (LLMProviderError, RuntimeError) as error:
        logger.warning("Cross-market model analysis skipped: %s", error)


def start_background_scheduler() -> BackgroundScheduler:
    """Start the scheduler used by the packaged desktop backend.

    The model interval is checked at execution time so changing the setting
    in the desktop UI takes effect without restarting the API process.
    """
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        collect_market_snapshot,
        trigger="interval",
        minutes=1,
        id="market-snapshot",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30,
    )
    scheduler.add_job(
        coordinate_cross_market,
        trigger="interval",
        minutes=1,
        id="cross-market-analysis",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )
    scheduler.start()
    return scheduler


def run() -> None:
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        collect_market_snapshot,
        trigger="interval",
        minutes=1,
        id="market-snapshot",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30,
    )
    scheduler.add_job(
        coordinate_cross_market,
        trigger="interval",
        minutes=auto_analysis_interval_minutes(),
        id="cross-market-analysis",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )
    logger.info("Market scheduler started; it collects once per minute during A-share trading sessions")
    scheduler.start()


if __name__ == "__main__":
    run()

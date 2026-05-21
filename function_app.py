import asyncio
import logging

import azure.functions as func

from src.orchestrator import run_digest

app = func.FunctionApp()

logger = logging.getLogger(__name__)


@app.timer_trigger(
    schedule="0 0 6 * * *",  # 6:00 AM UTC daily
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def news_digest_timer(timer: func.TimerRequest) -> None:
    if timer.past_due:
        logger.warning("Timer trigger is past due — running anyway")

    logger.info("News digest timer triggered")
    asyncio.run(run_digest())
    logger.info("News digest run complete")

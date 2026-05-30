from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from workers.worker import run_worker_once

scheduler = AsyncIOScheduler()


async def trigger_worker():

    try:
        print("🕑 Running scheduled worker...")

        await run_worker_once()

        print("✅ Scheduled worker completed")

    except Exception as e:
        print(f"❌ Scheduled worker failed: {e}")


def start_scheduler():

    scheduler.add_job(
        trigger_worker,
        trigger="interval",
        hours=24,
        next_run_time=datetime.now()
    )

    scheduler.start()

    print("🕒 Daily scheduler started; first run now, then every 24 hours")
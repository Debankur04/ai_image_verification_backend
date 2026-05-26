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
        trigger="cron",
        hour=2,
        minute=0
    )

    scheduler.start()

    print("🕒 Daily scheduler started (2:00 AM)")
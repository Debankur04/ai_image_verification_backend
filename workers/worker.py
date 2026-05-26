import json
import traceback
import signal
import asyncio
import uuid
import os

from pymongo import ReturnDocument

from workers import (
    email_worker,
    image_prep,
    pdf_creator,
    prediction
)

from supabase_client.supabase_init import supabase_admin
from supabase_client.storage_operations import (
    delete_images_create_report,
    create_signed_report_url
)

from supabase_client.db_operations import update_job_status
from job_storage.mongo_init import jobs_collection


# =========================
# CONFIG
# =========================
MAX_RETRIES = 5
MAX_IDLE_RETRIES = 5
POLL_INTERVAL = 2  # seconds


# =========================
# Graceful Shutdown
# =========================
shutdown_event = asyncio.Event()


def shutdown_handler(sig=None, frame=None):
    print("\n🛑 Worker shutdown requested. Stopping worker...")
    shutdown_event.set()


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)


# =========================
# Fetch Next Job
# =========================
async def fetch_next_job():
    """
    Atomically:
    - find QUEUED job
    - mark as PROCESSING
    - increment retry_count
    """

    # Pick the oldest QUEUED job (by created_at) to ensure FIFO processing.
    # Also treat documents missing a `status` field as QUEUED to handle
    # legacy enqueued items.
    job = await jobs_collection.find_one_and_update(
        {"$or": [{"status": "QUEUED"}, {"status": {"$exists": False}}]},
        {
            "$set": {"status": "PROCESSING"},
            "$inc": {"retry_count": 1}
        },
        sort=[("created_at", 1)],
        return_document=ReturnDocument.AFTER
    )

    return job


async def update_remote_status(job_id: str, status: str, report_path: str = None):
    await asyncio.to_thread(update_job_status, job_id, status, report_path)


def cleanup_local_pdf(report_filename: str):
    try:
        if os.path.exists(report_filename):
            os.remove(report_filename)
            print(f"🗑️  Cleaned up local PDF: {report_filename}")
    except Exception as exc:
        print(f"⚠️  Failed to delete local PDF: {exc}")


def get_batch_predictions(manifest: dict, bucket: str, input_prefix: str):
    results = []
    batch_images = []

    for filename in manifest.get("images", []):
        processed_img = image_prep.load_image(
            bucket_name=bucket,
            file_path=f"{input_prefix}{filename}"
        )
        batch_images.append(processed_img)

        if len(batch_images) == 2:
            predictions = prediction.predict_batch(batch_images)
            results.extend(predictions)
            batch_images.clear()

    if batch_images:
        predictions = prediction.predict_batch(batch_images)
        results.extend(predictions)

    return results


async def process_task(task: dict):
    job_id = task["job_id"]
    bucket = task["bucket"]
    input_prefix = task["input_prefix"]
    manifest_path = task["manifest_path"]
    report_prefix = task["report_prefix"]
    report_filename = task["report_filename"]

    print(f"\n🔄 Picked up job: {job_id}")
    await update_remote_status(job_id, "PROCESSING")

    try:
        manifest_bytes = supabase_admin.storage.from_(bucket).download(manifest_path)
        manifest = json.loads(manifest_bytes.decode("utf-8"))

        results = get_batch_predictions(manifest, bucket, input_prefix)

        pdf_creator.create_pdf_report(results=results, output_path=report_filename)

        report_path = delete_images_create_report(
            bucket=bucket,
            input_prefix=input_prefix,
            report_prefix=report_prefix,
            report_filename=report_filename
        )

        cleanup_local_pdf(report_filename)

        signed_url = create_signed_report_url(bucket=bucket, report_path=report_path)

        await update_remote_status(job_id, "COMPLETED", report_path)

        email_worker.send_report_email(
            user_email=task["user_email"],
            user_id=task["user_id"],
            report_link=signed_url
        )

        await handle_success(task)

        print(f"✅ Job {job_id} completed successfully")
        return True

    except Exception:
        print(f"❌ Job {job_id} failed")
        print(traceback.format_exc())

        retry_count = task.get("retry_count", 1)
        await handle_task_failure(task, job_id, retry_count)
        return False


async def handle_task_failure(task: dict, job_id: str, retry_count: int):
    if retry_count >= MAX_RETRIES:
        await update_remote_status(job_id, "FAILED")
        await handle_failure(task)
        print(f"⛔ Job {job_id} permanently failed")
        return

    await jobs_collection.update_one(
        {"_id": task["_id"]},
        {"$set": {"status": "QUEUED"}}
    )

    await update_remote_status(job_id, "QUEUED")
    print(f"🔁 Job {job_id} retry scheduled ({retry_count}/{MAX_RETRIES})")


async def _worker_loop(max_idle_retries: int, stop_on_empty: bool, respect_shutdown: bool):
    idle_retries = 0

    while True:
        if respect_shutdown and shutdown_event.is_set():
            print("🛑 Shutdown signal received. Stopping worker loop.")
            break

        print("⏳ Waiting for next job...")
        task = await fetch_next_job()

        if not task:
            idle_retries += 1
            print(f"📭 No jobs found ({idle_retries}/{max_idle_retries})")

            if idle_retries >= max_idle_retries:
                if stop_on_empty:
                    if respect_shutdown:
                        print("\n🛑 No jobs found for too long")
                        print("👋 Worker shutting down automatically")
                        shutdown_event.set()
                    else:
                        print("👋 Short worker run finished (no jobs)")
                    break

            await asyncio.sleep(POLL_INTERVAL)
            continue

        idle_retries = 0
        await process_task(task)

    print("👋 Worker stopped safely")


async def run_worker_once(max_idle_retries: int = MAX_IDLE_RETRIES):
    print("🚀 Short worker run started")
    await _worker_loop(max_idle_retries, stop_on_empty=True, respect_shutdown=False)


async def run_worker():
    print("🚀 Worker started")
    print("🧠 Press Ctrl+C to stop safely\n")
    await _worker_loop(MAX_IDLE_RETRIES, stop_on_empty=True, respect_shutdown=True)


# =========================
# Success Handler
# =========================
async def handle_success(job):
    await jobs_collection.delete_one({"_id": job["_id"]})


# =========================
# Failure Handler
# =========================
async def handle_failure(job):
    await jobs_collection.delete_one({"_id": job["_id"]})


# =========================
# Entry Point
# =========================
if __name__ == "__main__":
    asyncio.run(run_worker())
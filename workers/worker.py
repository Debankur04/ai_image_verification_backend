import json
import traceback
import signal
import sys
from workers import email_worker, image_prep, pdf_creator, prediction
from supabase_client.supabase_init import supabase_admin
from supabase_client.storage_operations import (
    delete_images_create_report,
    create_signed_report_url
)
import asyncio
from supabase_client.db_operations import update_job_status
from job_storage.mongo_init import jobs_collection

# =========================
# Graceful Shutdown
# =========================
shutdown_event = asyncio.Event()
def shutdown_handler(sig=None, frame=None):
    print("\n🛑 Worker shutdown requested. Stopping worker...")
    loop = asyncio.get_event_loop()
    loop.call_soon_threadsafe(shutdown_event.set)



signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)



async def fetch_next_job():
    job = await jobs_collection.find_one_and_update(
        {},                         # pick any job
        {"$inc": {"retry_count": 1}},
        return_document=True
    )
    return job

async def handle_success(job):
    await jobs_collection.delete_one({"_id": job["_id"]})
    # Update SQL → DONE



MAX_RETRIES = 5

async def handle_failure(job):
    if job["retry_count"] >= MAX_RETRIES:
        await jobs_collection.delete_one({"_id": job["_id"]})
        # Update SQL → FAILED


# =========================
# Worker Function
# =========================
async def run_worker():


    MAX_IDLE_RETRIES = 5
    idle_retries = 0

    print("🚀 Worker started")
    print("🧠 Press Ctrl+C to stop safely\n")

    while not shutdown_event.is_set():
        try:
            print("⏳ Waiting for next job...")
            task_json = await fetch_next_job()

            if not task_json:
                idle_retries += 1
                print(f"🫀 Worker alive, no jobs yet ({idle_retries}/{MAX_IDLE_RETRIES})")

                if idle_retries >= MAX_IDLE_RETRIES:
                    shutdown_handler()
                    return 

                continue

            idle_retries = 0

            task = task_json
            job_id = task["job_id"]

            print(f"\n🔄 Picked up job: {job_id}")

            try:
                print("🟡 Updating job status → PROGRESSED")
                update_job_status(job_id=job_id, status="PROGRESSED")

                bucket = task["bucket"]
                input_prefix = task["input_prefix"]
                manifest_path = task["manifest_path"]
                report_prefix = task["report_prefix"]
                report_filename = task["report_filename"]

                results = []
                batch_images = []

                manifest_bytes = (
                    supabase_admin.storage
                    .from_(bucket)
                    .download(manifest_path)
                )

                manifest = json.loads(manifest_bytes.decode("utf-8"))

                for filename in manifest["images"]:
                    processed_img = image_prep.load_image(
                        bucket_name=bucket,
                        file_path=f"{input_prefix}{filename}"
                    )

                    batch_images.append(processed_img)

                    if len(batch_images) == 2:
                        results.extend(prediction.predict_batch(batch_images))
                        batch_images.clear()

                if batch_images:
                    results.extend(prediction.predict_batch(batch_images))

                pdf_creator.create_pdf_report(
                    results=results,
                    output_path=report_filename
                )

                report_path = delete_images_create_report(
                    bucket=bucket,
                    input_prefix=input_prefix,
                    report_prefix=report_prefix,
                    report_filename=report_filename
                )

                signed_url = create_signed_report_url(
                    bucket=bucket,
                    report_path=report_path
                )

                print("🟢 Updating job status → DONE")
                update_job_status(
                    job_id=job_id,
                    status="DONE",
                    report_path=report_path
                )

                email_worker.send_report_email(
                    user_email=task["user_email"],
                    user_id=task["user_id"],
                    report_link=signed_url
                )
                await handle_success(task_json)

                # r.lrem(PROCESSING_QUEUE, 1, task_json)
                print(f"✅ Job {job_id} completed")

            except Exception:
                print(f"❌ Job {job_id} failed")
                print(traceback.format_exc())
                

                if task["retry_count"] >= MAX_RETRIES:
                    update_job_status(job_id=job_id, status="FAILED")
                    await handle_failure(task)
                    print(f"⛔ Job {job_id} permanently failed")
                else:
                    # Retry will happen later
                    update_job_status(job_id=job_id, status="QUEUED")
                    print(
                    f"🔁 Job {job_id} failed, retrying "
                    f"({task['retry_count']}/{MAX_RETRIES})"
                    )

        except KeyboardInterrupt:
            shutdown_handler()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_worker())

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Depends,
)
from job_storage.mongo_init import jobs_collection

from fastapi.responses import RedirectResponse
from typing import List
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from supabase_client.supabase_init import supabase_public
from supabase_client.auth import signup, signin, signout
from supabase_client.storage_operations import upload_images_and_manifest, create_signed_report_url
from supabase_client.db_operations import (
    insert_job,
    delete_job,
    returning_all_jobs
)
from schema import AuthPayload, JobCreateResponse
from auth_dependency import get_current_user
from workers.worker import run_worker
import uuid

from scheduler import start_scheduler


# ---------------- App ----------------
app = FastAPI(
    title="AI Image Detection API",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    start_scheduler()
    
async def enqueue_job(job_data: dict):
    # Ensure queue metadata is present so worker can find the job
    job_data.setdefault("status", "QUEUED")
    job_data.setdefault("retry_count", 0)

    await jobs_collection.insert_one(job_data)


# ---------------- Constants ----------------
BUCKET = "user-uploads"
MAX_IMAGES = 100
MAX_IMAGE_SIZE_MB = 5


# ============================================================
# Health
# ============================================================

@app.get("/health")
def health():
        return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
        }
    

# ============================================================
# Auth APIs
# ============================================================

@app.post("/auth/signup")
def signup_api(payload: AuthPayload):
    return signup(
         payload.email,
         payload.password
    )


@app.post("/auth/signin")
def signin_api(payload: AuthPayload):
    return signin(
        payload.email,
        payload.password
    )


@app.post("/auth/signout")
def signout_api():
    return signout()

# ============================================================
# Create Job
# ============================================================

@app.post("/jobs", response_model=JobCreateResponse)
async def create_job(
    images: List[UploadFile] = File(...),
    user=Depends(get_current_user)
):
    if not images:
        raise HTTPException(status_code=400, detail="No images provided")

    if len(images) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail="Too many images")

    image_payload = []

    for img in images:
        content = await img.read()
        size_mb = len(content) / (1024 * 1024)

        if size_mb > MAX_IMAGE_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail=f"{img.filename} exceeds {MAX_IMAGE_SIZE_MB}MB"
            )

        image_payload.append((img.filename, content))

    # ---------------- Create Job ----------------
    job_id = insert_job(user_id=user["user_id"], status="QUEUED")

    base_path = f"users/{user['user_id']}/jobs/{job_id}"
    input_prefix = f"{base_path}/input"
    manifest_path = f"{base_path}/manifest.json"
    report_prefix = f"{base_path}/report"

    manifest = {
        "job_id": job_id,
        "user_id": user["user_id"],
        "images": [name for name, _ in image_payload],
        "total_images": len(image_payload),
        "created_at": datetime.utcnow().isoformat()
    }

    upload_images_and_manifest(
        bucket=BUCKET,
        images=image_payload,
        manifest=manifest,
        manifest_remote_path=manifest_path,
        input_prefix=input_prefix
    )

    # ---------------- Enqueue Job (MongoDB) ----------------
    # Use a unique report filename to avoid collisions and overwrite issues
    report_filename = f"report_{uuid.uuid4().hex}.pdf"

    payload = {
        "job_id": job_id,
        "user_id": user["user_id"],
        "user_email": user["email"],
        "bucket": BUCKET,
        "input_prefix": f"{input_prefix}/",
        "manifest_path": manifest_path,
        "report_prefix": f"{report_prefix}/",
        "report_filename": report_filename,
        "created_at": datetime.utcnow().isoformat()
    }

    await enqueue_job(payload)

    return JobCreateResponse(job_id=job_id, status="QUEUED")

# ============================================================
# List Jobs
# ============================================================

@app.get("/jobs")
def list_jobs(user=Depends(get_current_user)):
    return returning_all_jobs(user["user_id"])

# ============================================================
# Job Status
# ============================================================

@app.get("/jobs/{job_id}")
def get_job(job_id: str, user=Depends(get_current_user)):
    job = (
        supabase_public
        .table("jobs")
        .select("*")
        .eq("job_id", job_id)
        .eq("user_id", user["user_id"])
        .single()
        .execute()
    )

    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found")

    return job.data

# ============================================================
# Download Report (auto-download)
# ============================================================

@app.get("/jobs/{job_id}/report")
def download_report(job_id: str, user=Depends(get_current_user)):
    job = (
        supabase_public
        .table("jobs")
        .select("report_path")
        .eq("job_id", job_id)
        .eq("user_id", user["user_id"])
        .single()
        .execute()
    )

    if not job.data or not job.data["report_path"]:
        raise HTTPException(status_code=404, detail="Report not ready")

    signed_url = create_signed_report_url(
        bucket=BUCKET,
        report_path=job.data["report_path"]
    )

    return RedirectResponse(url=signed_url)

# ============================================================
# Delete Job
# ============================================================

@app.delete("/jobs/{job_id}")
def delete_job_api(job_id: str, user=Depends(get_current_user)):
    job = (
        supabase_public
        .table("jobs")
        .select("job_id")
        .eq("job_id", job_id)
        .eq("user_id", user["user_id"])
        .single()
        .execute()
    )

    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found")

    delete_job(job_id)

@app.post("/internal/run-worker")
async def run_worker_once_api():
    """Manually triggers the worker once (bounded polling).

    This endpoint runs a short-lived worker loop that polls MongoDB
    up to `MAX_IDLE_RETRIES` times before returning. Useful for
    triggering work from API calls without starting the long-running
    background worker.
    """
    from workers.worker import run_worker_once as run_worker_once_fn

    await run_worker_once_fn()

    return {"status": "finished", "message": "Worker run completed"}
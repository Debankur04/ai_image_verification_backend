
# AI Image Classifier – Backend Service

Production-ready FastAPI backend for AI-vs-Real image classification using a pre-trained CNN model.

This repository contains ONLY the backend (inference, workers, APIs, deployment). Model training lives in aseparate repository.

## 1. Overview

 This backend provides:
 - User authentication (Supabase Auth)
 - Job-based image processing
 - Batch CNN inference
 - PDF report generation
 - Redis-based background job queue
 - Email delivery of reports
 - Fully Dockerized deployment

 The system is designed for production stability and cloud deployment.

## 2. Tech Stack

 - FastAPI (API framework)
 - TensorFlow / Keras (model inference)
 - Redis (job queue)
 - Supabase (Auth, DB, Storage)
 - ReportLab (PDF generation)
 - Resend (email delivery)
 - Docker (containerization)

## 3. Project Structure

 .
 ├── inference/
 │   ├── app.py            # FastAPI entrypoint
 │   ├── worker.py         # Background worker logic
 │   ├── workers/          # Email, PDF, image helpers
 │   └── ...
 │
 ├── supabase_client/
 │   ├── supabase_init.py
 │   ├── db_operations.py
 │   └── storage_operations.py
 │
 ├── models/
 │   └── ai_vs_real_cnn.keras
 │
 ├── Requirements.txt
 ├── Dockerfile
 └── README.sh



## 4. Environment Variables

 Create a `.env` file in the project root:
```
 SUPABASE_URL=your_supabase_url
 SUPABASE_ANON_KEY=your_anon_key
 SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

 REDIS_URL=redis://host:port

 RESEND_API_KEY=your_resend_api_key

 MODEL_PATH=models/ai_vs_real_cnn.keras
```

## 5. Local Installation (Without Docker)

Recommended only for development/testing.

 1. Create virtual environment:
 ```
    python -m venv .venv
    source venv/bin/activate  (Linux/Mac)
    venv\Scripts\activate     (Windows)
```
 2. Install dependencies:
    ```
    pip install --upgrade pip
    pip install -r Requirements.txt
    ```
 3. Run API:
    ```
    uvicorn inference.app:app --reload
    ```
 4. Run worker (separate terminal):
    ```
    python inference/worker.py
    ```
## 6. Docker Installation (Recommended)

 This is the preferred way to run the backend.

 1. Build image:
    docker build -t ai-image-backend .

 2. Run container:
    docker run -p 8000:8000 --env-file .env ai-image-backend

 API will be available at:
 http://localhost:8000


## 7. API Endpoints (Core)
- Health Check
 ```
 GET  /health
```
- Authentication
 ```
 POST /auth/signup
 POST /auth/signin
 POST /auth/signout
```
- Jobs
 ```
 POST /jobs/create
 GET  /jobs
 DELETE /jobs/{job_id}
```
- Reports
```
 GET /reports/{job_id}
```

## 8. Background Worker

 - Uses Redis as a queue
 - Processes images in batches
 - Generates PDF reports
 - Uploads report to Supabase Storage
 - Sends email with signed download link

 Worker can be:
 - Run as a separate container
 - Triggered via internal API
 - Scheduled externally (cron / cloud scheduler)



## 9. Deployment

 This backend is designed to be deployed using:
 - Docker Hub
 - RENDER / Railway / Fly.io / Cloud Run / similar platforms

 The container exposes port 8000 and requires environment variables for configuration.

 Training code and datasets are intentionally excluded from this repository.

## 10. Notes

 - This repository contains inference-only logic. 
 - Model training and experimentation are handled in a separate repository. 
 [Click here for the repository](https://github.com/Debankur04/ai_image_classifier)
 - The model file is treated as an artifact.

 This separation ensures:
 - Smaller Docker images
 - Stable deployments
 - Cleaner architecture


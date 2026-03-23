# AI Image Verification & Bias Detection Backend

## Overview
This backend powers an advanced AI suite focused on digital verification. It now features two primary engines:
1. **AI Image Verification**: Classifies images as Real or AI-Generated using a fast ONNX-based CNN model.
2. **News Bias Classification (New)**: Analyzes news article URLs to determine if their content is right-leaning, left-leaning, or central, giving users a better understanding of media bias.

## Key Features

### Image Verification Core
- **Batch Async Inference**: Users can upload up to 100 images at a time. A background worker picks up the job from the queue, processes them using batching logic, creates a comprehensive PDF report, uploads it to Supabase storage, and emails the user the result link.
- **Normal Sync Inference (Update)**: Users can directly request instant inference for single images, getting immediate JSON predictions without waiting for background worker queues.

### Media Analysis Core
- **News Bias Checker**: Give the system a URL to an article, and it will fetch the content to classify its ideological leanings (Left, Right, or Center), aiding in media literacy.

## Setup & Running

**Prerequisites:**
- Python 3.10+
- MongoDB instance (for job storage)
- Supabase account (for Authentication and Object Storage)
- SendGrid / Resend (for email callbacks)

**1. Install Dependencies**
```bash
pip install -r Requirements.txt
```

**2. Environment Variables**
Configure your `.env` file with Supabase credentials, MongoDB URI, and your LLM API keys for the news classifier.

**3. Run the API App**
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

**4. Run the Async Worker**
If using the batch job queues, run the worker in a separate terminal:
```bash
python -m workers.worker
```

## Upcoming Suggested Upgrades (Roadmap)
As part of our continuous expansion, the following feature upgrades are highly recommended for the next development sprint:
1. **API Rate Limiting**: Implement request throttling to prevent exploitation of the inference endpoints.
2. **B2B API Key Management**: Allow programmatic access for other businesses to use the verification engine via API Tokens.
3. **Webhook Notifications**: Shift from email-only job completion to real-time webhook push events for seamless app integrations.
4. **Video Deepfake Processing**: Extend the ONNX models to parse video frames and detect manipulated media in motion.
5. **Caching Layer**: Store results for previously checked News URLs or image checksums to save on compute resources.

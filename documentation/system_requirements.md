# System Requirements: AI Image Verification Backend (v2 Updates)

## 1. Introduction
This document outlines the system requirements and technical design for the v2 updates to the AI Image Verification Backend. Expanding from the core real vs. fake image detection, the system now includes news article URL bias classification and supports a transition back to normal (synchronous) inference mode for single-image verification.

## 2. Functional Requirements

### 2.1 News URL Bias Classification
- **Input**: The system MUST accept a News Article URL from the authenticated user.
- **Process**: The system MUST scrape or extract text/metadata from the URL and analyze its political or ideological leanings (Right-leaning, Left-leaning, or Central).
- **Output**: The system MUST return the classification result to the user, providing a general understanding of the article's bias.

### 2.2 Normal (Synchronous) Inference Mode
- **Input**: User uploads a single image (or small batch).
- **Process**: The system MUST bypass the asynchronous job processing queue (MongoDB + background worker) and directly route the image to the `predict_batch` ONNX classification engine in the active request scope.
- **Output**: The system MUST return the Real/Fake prediction and confidence score instantly in the HTTP response.

### 2.3 Proposed Upgrades
The following features are architecturally recommended for future development:
- **API Key Management**: Support for external clients (B2B integration) via generated API credentials instead of just user-based session auth.
- **Rate Limiting Engine**: API throttling to prevent abuse of the heavy inference and LLM endpoints.
- **Webhook Callbacks**: Instead of relying solely on emails (`email_worker.py`), allow clients to register webhook URLs for async job completion notifications.
- **Video & Audio Deepfake Detection**: Expand inference capabilities to process frame-by-frame video deepfakes and synthesize audio checks.
- **Caching Layer**: Store results for known URLs or Image checksums.

## 3. Non-Functional Requirements
- **Performance**: Normal inference turnaround should be under 2 seconds per image. URL Bias checks should be under 3 seconds.
- **Scalability**: The News URL checking module should be able to integrate with external LLM APIs (e.g., Groq, OpenAI) to scale effectively without blocking the image inference instances.

## 4. Architectural Changes Needed
- **Endpoints Needed**:
  - `POST /news/analyze`: Accepts `{ "url": "string" }`.
  - `POST /predict/sync`: Accepts `UploadFile` for immediate verification.
- **Dependencies needed**:
  - Web scraping library (e.g. `beautifulsoup4` or `trafilatura`) for URL content extraction.
  - LLM integration SDK to process text bias based on a predefined prompt.

import os
from pathlib import Path
import numpy as np
import onnxruntime as ort

# ---------- CONFIG ----------
MODEL_PATH = Path("models") / "ai_vs_real_cnn_frozen.onnx"

# ---------- LOAD ONNX MODEL (FAIL FAST) ----------
if not MODEL_PATH.exists():
    raise FileNotFoundError(f"Model not found at {MODEL_PATH}")

print("🔄 Loading ONNX model...")

SESSION = ort.InferenceSession(
    str(MODEL_PATH),
    providers=["CPUExecutionProvider"]
)

INPUT_NAME = SESSION.get_inputs()[0].name
OUTPUT_NAME = SESSION.get_outputs()[0].name

# ---------- STARTUP SANITY CHECK ----------
_dummy = np.zeros((2, 224, 224, 3), dtype=np.float32)
SESSION.run([OUTPUT_NAME], {INPUT_NAME: _dummy})

print("✅ ONNX model loaded and verified")

# ---------- HELPERS ----------
def ensure_valid_batch(images):
    if not (1 <= len(images) <= 2):
        raise ValueError("Batch must contain 1 or 2 images.")

# ---------- PREDICTION ----------
def predict_batch(images, threshold=0.40):
    """
    images: list of 1 or 2 NumPy arrays, each (224, 224, 3)
    """
    ensure_valid_batch(images)

    batch = np.stack(images, axis=0).astype(np.float32)

    probs = SESSION.run(
        [OUTPUT_NAME],
        {INPUT_NAME: batch}
    )[0]  # shape: (B, 1)

    results = []
    for i, prob in enumerate(probs):
        p = float(prob[0])

        label = "AI Generated" if p >= threshold else "Real"
        confidence = p if p >= threshold else 1 - p

        results.append({
            "prediction": label,
            "confidence": round(confidence * 100, 2),
            "image_tensor": images[i]
        })
    return results

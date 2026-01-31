import os
from pathlib import Path
import tensorflow as tf
from tensorflow import keras

# ---------- CONFIG ----------
MODEL_PATH = Path("models") / "ai_vs_real_cnn.keras"

# ---------- LAZY MODEL LOAD ----------
_model = None

def get_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
        _model = keras.models.load_model(MODEL_PATH)
    return _model


# ---------- HELPERS ----------
def ensure_valid_batch(images):
    if not (1 <= len(images) <= 2):
        raise ValueError("Batch must contain 1 or 2 images.")


# ---------- PREDICTION ----------
def predict_batch(images, threshold=0.40):
    """
    images: list of 1 or 2 tensors, each (224, 224, 3)
    """

    ensure_valid_batch(images)

    batch = tf.stack(images, axis=0)

    model = get_model()
    probs = model.predict(batch)

    results = []
    for i, prob in enumerate(probs):
        p = float(prob[0])

        label = "AI Generated" if p >= threshold else "Real"
        confidence = p if p >= threshold else 1 - p

        results.append({
            "prediction": label,
            "confidence": round(confidence * 100, 2)
        })

    return results

import os
import io
import base64
import logging

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from kokoro_onnx import Kokoro

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kokoro-tts")

app = FastAPI(title="Kokoro TTS Service")

MODEL_PATH = os.getenv(
    "KOKORO_MODEL_PATH",
    "/app/models/kokoro-v1.0.onnx"
)
VOICES_PATH = os.getenv(
    "KOKORO_VOICES_PATH",
    "/app/models/voices-v1.0.bin"
)

kokoro = None


class SynthesisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    voice: str = "af_heart"
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


@app.on_event("startup")
def load_model():
    global kokoro

    logger.info("Loading Kokoro ONNX model...")
    kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
    logger.info("Kokoro model loaded successfully")


@app.get("/health")
def health():
    return {
        "ok": kokoro is not None,
        "provider": "kokoro-onnx",
        "model_loaded": kokoro is not None
    }


@app.post("/synthesize")
def synthesize(req: SynthesisRequest):
    if kokoro is None:
        raise HTTPException(
            status_code=503,
            detail="Kokoro model is not loaded"
        )

    try:
        samples, sample_rate = kokoro.create(
            req.text,
            voice=req.voice,
            speed=req.speed,
            lang="en-us"
        )

        audio_buffer = io.BytesIO()

        sf.write(
            audio_buffer,
            np.asarray(samples),
            sample_rate,
            format="WAV",
            subtype="PCM_16"
        )

        audio_base64 = base64.b64encode(
            audio_buffer.getvalue()
        ).decode("utf-8")

        return {
            "audio_base64": audio_base64,
            "audio_format": "wav",
            "sample_rate": sample_rate,
            "voice": req.voice
        }

    except Exception as exc:
        logger.exception("Speech synthesis failed")
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )

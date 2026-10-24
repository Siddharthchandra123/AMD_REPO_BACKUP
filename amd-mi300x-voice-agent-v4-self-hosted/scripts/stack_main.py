"""Readiness monitor for the AMD MI300X Voice Agent Compose stack.

Docker Compose starts dependency containers; the main service observes readiness.
It does not mount /var/run/docker.sock or control the Docker daemon.
"""
import os
import signal
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CHECKS = {
    "LLM (ROCm vLLM)": "http://llm:8000/v1/models",
    "Whisper ASR": "http://asr:9000/health",
    "Kokoro TTS": "http://tts:9001/health",
    "Qdrant": "http://qdrant:6333/healthz",
    "FastAPI": "http://api:8000/ready",
    "React UI": "http://web/",
}
MARKER = Path("/tmp/voice-agent-stack-ready")
INTERVAL = max(5, int(os.getenv("STACK_INTERVAL_SECONDS", "15")))
TIMEOUT = max(1, float(os.getenv("STACK_REQUEST_TIMEOUT_SECONDS", "5")))
running = True


def shutdown(_sig, _frame):
    global running
    running = False


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)


def probe(url):
    try:
        req = Request(url, headers={"User-Agent": "voice-agent-main/1.0"})
        with urlopen(req, timeout=TIMEOUT) as response:
            code = response.status
            # Ensure the model endpoint is answering, not just accepting TCP.
            body = response.read(4096) if "/v1/models" in url else b""
            if "/v1/models" in url and b"data" not in body:
                return "not-ready (model listing missing)"
            return "ready" if 200 <= code < 300 else f"HTTP {code}"
    except HTTPError as exc:
        return f"HTTP {exc.code}"
    except (URLError, TimeoutError, OSError) as exc:
        return f"unavailable ({type(exc).__name__})"


print("Main service online; awaiting six application services.", flush=True)
previous = None
while running:
    states = {name: probe(url) for name, url in CHECKS.items()}
    ready = all(status == "ready" for status in states.values())
    if ready:
        MARKER.touch()
    else:
        MARKER.unlink(missing_ok=True)
    state_tuple = tuple(states.items())
    if state_tuple != previous:
        for name, state in states.items():
            print(f"  {name}: {state}", flush=True)
        print("STACK READY" if ready else "Waiting for dependencies...", flush=True)
        previous = state_tuple
    for _ in range(INTERVAL):
        if not running:
            break
        time.sleep(1)
MARKER.unlink(missing_ok=True)
print("Main readiness monitor stopped.", flush=True)

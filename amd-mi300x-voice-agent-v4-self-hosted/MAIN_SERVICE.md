# One-command launch: `main` service

The `main` Compose service is a **readiness monitor and orchestration entrypoint**. Docker Compose itself starts all declared dependencies. The `main` container **does not** run Docker-in-Docker or mount the Docker daemon socket.

## Start all seven containers with one command

From the project directory on the AMD MI300X host:

```bash
docker compose --profile gpu up -d --build main
```

This command starts **llm, asr, tts, qdrant, api, web, and main**. The `main` service has the same `gpu` profile as `llm`, so `docker compose up -d --build main` also works when targeting it explicitly.

The first run may download the ROCm vLLM image, Python dependencies, Whisper model, and missing Kokoro `kokoro-v1.0.onnx` (from the pinned official upstream `model-files-v1.0` release). The TTS model is **not included** in the supplied project archive. The build requires internet access when provisioning it for the first time. Ensure the required model licenses and provenance meet your deployment policies.

Docker Compose `depends_on` starts the dependencies but does not guarantee they are ready. The `main` container continuously checks all six services and reports Docker health state `healthy` only after all service HTTP endpoints respond successfully.

## Observe progress

```bash
docker compose --profile gpu logs -f main
```

On success, logs contain `STACK READY`. Before readiness, `main` shows which service is still loading. Model initialization can take several minutes.

Check the stack:

```bash
docker compose --profile gpu ps -a
```

Open the web UI at `http://<HOST>:8080` (use an SSH tunnel or a trusted private network for remote access). The API listens at `:8000`, LLM host API at `:8001`, ASR at `:9000`, TTS at `:9001`, and Qdrant at `:6333`.

## Stop or restart

```bash
docker compose --profile gpu stop
# Stop and remove application containers; volumes are preserved.
docker compose --profile gpu down
# Restart containers after `stop` (not after `down`):
docker compose --profile gpu start
# After `down`, recreate containers using the one-command launch:
docker compose --profile gpu up -d --build main
```

**Do not use `down -v`** unless you intend to delete named volumes such as Qdrant storage and the Hugging Face cache.

## What the main service does (and does not do)

- Starts all service containers through Compose's `depends_on` graph when you target `main`.
- Reports readiness across the stack, including the LLM model listing.
- Restarts independently if its process exits because `restart: unless-stopped` is configured.
- Does not control the Docker daemon directly or restart crashed dependencies. Those services retain their original Docker restart policies.
- Does not guarantee full functional correctness; perform a real voice request after the services report ready.
- Does not make the system production-secure or publicly deployable; authentication, network access controls, and sizing tests remain separate tasks.

## Fresh-install prerequisites

- Linux host with AMD ROCm-supported MI300X driver and `/dev/kfd` / `/dev/dri`
- Modern Docker Engine and Docker Compose v2
- Internet access for first-time image/model downloads
- GPU memory; vLLM can reserve most available VRAM
- Available host ports 8080, 8000, 8001, 9000, 9001, 6333

## Jupyter one-cell launch

```python
import subprocess
from pathlib import Path

project = Path('/root/amd-mi300x-voice-agent-v4-self-hosted')
subprocess.run(
    ['docker','compose','--profile','gpu','up','-d','--build','main'],
    cwd=project, check=True
)
```

The notebook cell prints live build/start logs without needing a second notebook cell.

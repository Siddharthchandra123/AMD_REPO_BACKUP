# AMD Instinct MI300X Self-Hosted Voice AI
## Technical Deployment, Verification & Benchmarking Playbook

**Edition:** Source-grounded working draft · 24 October 2026  
**Basis:** Supplied `project(2).zip`, project directory `amd-mi300x-voice-agent-v4-self-hosted/`  
**Audience:** ML engineers, GPU platform engineers, application developers, infrastructure operators  
**Status:** Demonstrated prototype; **not** a production-certified deployment.

> **Evidence convention:** **Implemented** means present in the uploaded source. **Measured** means present in archived benchmark output. **Not verified in this package** means that the source archive alone does not establish a working clean-room deployment or that a dependency is missing. **Future work** is not a demonstrated feature.

---

## 1. Mission and deployment outcome

Deploy a self-hosted voice assistant with browser text and microphone interaction, local automatic speech recognition (ASR), a ROCm-enabled LLM hosted on an AMD Instinct MI300X, local speech synthesis, and a Qdrant-backed context-retrieval interface. The user can ask by text or uploaded audio and receive an answer and, where enabled, a WAV audio response.

**Primary deployment outcomes:**

- Browser frontend reachable on host port `8080`.
- FastAPI gateway reachable on host port `8000`.
- Qwen2.5-3B-Instruct served through a vLLM OpenAI-compatible API on host port `8001`.
- Whisper Small ASR on host port `9000` (currently CPU implementation).
- Kokoro ONNX TTS on host port `9001` (requires model files).
- Qdrant vector-store endpoint on host port `6333`.
- Successful `POST /voice` response with transcript, answer, and Base64-encoded WAV audio.

### Out-of-scope claims

The current implementation has **not** demonstrated sustained concurrent voice-user capacity, production-grade security, semantic embedding quality, reliable long-running service-level objectives, or GPU-accelerated Whisper. The separate `services/asr-rocm/` directory is an exploratory candidate and is not wired into `docker-compose.yml`.

---

## 2. Architecture and ownership

```text
Browser + microphone/speakers
        |
        v
React + TypeScript + Vite (built assets served by Nginx :8080)
        | /api/* -> HTTP; /ws/* -> WebSocket
        v
FastAPI orchestration (:8000)
        |              |                 |                 |
        v              v                 v                 v
Whisper Small       vLLM / Qwen      Kokoro ONNX         Qdrant
CPU ASR :9000       GPU LLM :8001     TTS :9001           :6333
                       |
                       v
                AMD Instinct MI300X / ROCm
```

**Deployment source:** `docker-compose.yml`. The GPU is passed through to `llm` using `/dev/kfd` and `/dev/dri`; the `asr` service has no GPU passthrough. `api` reaches its dependencies using Compose service hostnames (`llm`, `asr`, `tts`, `qdrant`). Nginx proxies `/api/` to FastAPI and `/ws/` to the WebSocket endpoint.

### HTTP voice workflow — as implemented

1. Browser records an audio blob using the `MediaRecorder` interface.
2. `services/web/src/App.tsx` sends multipart field `file` to `/api/voice`.
3. Nginx proxies the request to FastAPI `POST /voice`.
4. FastAPI forwards the audio to `POST http://asr:9000/transcribe`.
5. The transcript enters the FastAPI chat handler with its **default** session ID for this route.
6. Chat retrieves context from Qdrant using the current deterministic placeholder embedding function.
7. The orchestrator invokes Qwen through vLLM's OpenAI-compatible streaming API, accumulating text into the final answer.
8. FastAPI calls `POST http://tts:9001/synthesize` and receives Base64 WAV.
9. FastAPI returns one JSON payload: `transcript`, `answer`, and TTS audio metadata.
10. React displays the conversation and plays the returned WAV.

**Important distinction:** This HTTP `/voice` route returns a **completed** response; it does not stream microphone audio or deliver first-audio chunks progressively. FastAPI separately implements `/ws/realtime/{session_id}` for token and sentence-audio streaming; the archived React frontend uses HTTP fetch calls, not that WebSocket route.

### Text chat workflow — as implemented

`React /api/chat → FastAPI /chat → Qdrant query → orchestrator → vLLM → JSON answer`. When auto-speech is enabled, React separately calls `/api/tts → FastAPI /tts → Kokoro`.

---

## 3. Artifact and dependency inventory

| Location | Role | Archive observation |
|---|---|---|
| `docker-compose.yml` | Single-host orchestration | Present; six named services |
| `services/api/app/` | Chat, voice, RAG, LLM, sessions, WebSocket | Present |
| `services/asr/` | CPU Whisper Small transcription | Present |
| `services/asr-rocm/` | Candidate ROCm ASR build | Present, not referenced by Compose |
| `services/tts/` | Kokoro ONNX synthesis | Present |
| `services/web/` | React frontend and Nginx image | Present; `dist/` included |
| `benchmarks/` | Raw and consolidated results | Present |
| `BENCHMARKS.md` | Experimental report | Present |
| `kubernetes/` | Partial API-only manifest | Present; not a full cluster deployment |
| `services/tts/models/voices-v1.0.bin` | Kokoro voice data | Present |
| `services/tts/models/kokoro-v1.0.onnx` | Kokoro acoustic model | **Missing from ZIP** |
| `.env.example` | Template mentioned by `SELF_HOSTED.md` | **Missing from ZIP** |

The uploaded archive includes thousands of `services/web/node_modules/` entries and Jupyter workspace/checkpoint files. They are development byproducts; do not treat them as project source or package them in a public release.

---

## 4. Environment prerequisites and safety checks

**Expected environment:** Linux GPU host with an AMD Instinct MI300X, supported ROCm driver stack, Docker and Docker Compose, adequate VRAM/disk, and outbound access for container/model downloads. Original development used a ROCm vLLM container and a separately verified ROCm 7.2 PyTorch test container. Verify host compatibility rather than assuming image `:latest` is interchangeable across ROCm releases.

### Check 4.1 — Confirm GPU detection

```bash
ls -l /dev/kfd /dev/dri
amd-smi monitor --vram --gpu 0
```

**Pass:** relevant device nodes exist and the GPU is visible. **Fail:** absence of device files, device permission errors, or an unavailable `amd-smi` command. Confirm the exact hardware/driver environment before proceeding.

### Check 4.2 — Docker and capacity

```bash
docker --version
docker compose version
df -h /
docker system df
```

**Pass:** Docker and Compose work, and sufficient disk space is available for sizable model images. Inspect VRAM availability if an existing vLLM service already reserves most of the card.

### Check 4.3 — Required model artifacts

```bash
test -s services/tts/models/voices-v1.0.bin && echo 'Voices: found'
test -s services/tts/models/kokoro-v1.0.onnx && echo 'Kokoro ONNX: found'
```

**Current ZIP warning:** The ONNX model is **not bundled**. Download the exact supported model artifact from the model's official distribution and verify its checksum/license before building TTS. Do not claim a clean build is reproducible until this dependency is supplied.

---

## 5. Configure the project

From the extracted project root:

```bash
export VLLM_MODEL='Qwen/Qwen2.5-3B-Instruct'
export HF_TOKEN=''  # set securely only when an authenticated model download is required

docker compose --profile gpu config
```

**Pass:** Compose configuration renders successfully with six services (`api`, `llm`, `asr`, `tts`, `qdrant`, `web`). **Fail:** unresolved interpolation errors or missing compose file.

**Security:** Never include genuine Hugging Face tokens, cloud keys, private SSH keys, or sensitive transcript data in a public archive or notebook. Bind published ports to loopback or restrict host firewall/ingress rules as appropriate; the current Compose file publishes ports without an explicit loopback restriction.

---

## 6. Build and deploy

Only run once all required model files are present and you are prepared to download sizable images:

```bash
docker compose --profile gpu up -d --build
```

Then inspect:

```bash
docker compose --profile gpu ps -a
docker compose --profile gpu logs --tail=80 asr tts api llm web qdrant
```

**Pass:** containers remain running and eventually respond to functional requests. **Note:** initial vLLM model load can take time; a running container alone is not proof that inference is ready.

For a known-good running deployment, do **not** rebuild every service merely to validate documentation. Use the read-only checks below instead.

---

## 7. Service acceptance tests

### 7.1 vLLM readiness and inference

```bash
curl -fsS http://127.0.0.1:8001/v1/models
```

**Pass:** HTTP 200 with a model list. Then submit a short chat-completion request to verify generated text (model availability alone is a weaker check).

### 7.2 ASR and TTS health

```bash
curl -fsS http://127.0.0.1:9000/health
curl -fsS http://127.0.0.1:9001/health
```

**Pass:** status 200 and expected health fields. In particular, the TTS response should report `model_loaded: true`.

### 7.3 Data store and API

```bash
curl -fsS http://127.0.0.1:6333/healthz
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
curl -fsS http://127.0.0.1:8000/metrics | head
```

**Caution:** `GET /ready` currently always returns `{"status":"ready"}`; it does **not** probe dependency reachability. Verify dependencies separately.

### 7.4 Text chat

```bash
curl -fsS http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"text":"Say hello in one short sentence.","session_id":"playbook-smoke"}'
```

**Pass:** JSON contains a nonempty `answer`.

### 7.5 Audio transcription

```bash
curl -fsS http://127.0.0.1:9000/transcribe \
  -F 'file=@benchmarks/kokoro_test.wav;type=audio/wav'
```

**Pass:** JSON contains `text` corresponding to the input. `kokoro_test.wav` is included in the supplied archive.

### 7.6 Complete voice loop

```bash
curl -fsS http://127.0.0.1:8000/voice \
  -F 'file=@benchmarks/kokoro_test.wav;type=audio/wav' \
  -o /tmp/voice-playbook-response.json
```

Verify that the JSON contains `transcript`, `answer`, `audio_base64`, `audio_format`, and `sample_rate`. Do not print the complete Base64 response to logs. In the previously recorded experiment, the first complete voice request returned HTTP 200 and generated a WAV response.

### 7.7 Browser acceptance

Visit `http://HOST:8080` (subject to firewall/network settings). Validate typed chat, microphone permission, recording, transcription text, synthesized playback, pause, and replay. Browser microphone capture generally requires `localhost` or a secure HTTPS origin; serving the site directly over an unsecured remote-host HTTP origin may block microphone access.

---

## 8. Benchmarks — actual results recorded in archive

All metrics below are evidence retained in `benchmarks/` and `BENCHMARKS.md`, **not predictions**.

### 8.1 vLLM short-batch tests

| Simultaneous requests | Success | Mean time to first token | Mean request latency | Recorded aggregate output throughput |
|---:|---:|---:|---:|---:|
| 1 | 5/5 | 14.6 ms | 349.5 ms | Not recorded as batch throughput |
| 5 | 5/5 | 27.8 ms | 531.1 ms | 1,198.05 tokens/s |
| 10 | 10/10 | 41.4 ms | 509.2 ms | 2,484.62 tokens/s |
| 25 | 25/25 | 77.3 ms | 606.5 ms | 5,189.73 tokens/s |
| 50 | 50/50 | 104.3 ms | 690.1 ms | 8,992.70 tokens/s |

Model: `Qwen/Qwen2.5-3B-Instruct`; output target: 128 tokens per request. Aggregated throughput figures are from recorded earlier run-level summaries; per-request CSVs do not retain batch wall-clock intervals. These tests **do not** establish 50 simultaneous voice users or stable long-duration throughput.

### 8.2 Speech and full voice (3 sequential runs per component)

| Component | Success | Mean latency | Minimum | Maximum | Other observed metrics |
|---|---:|---:|---:|---:|---|
| Whisper Small (CPU) | 3/3 | **28.8342 s** | 28.8114 s | 28.8742 s | WER 0% on one synthetic sentence; RTF ~3.173 |
| Kokoro ONNX | 3/3 | **1.6398 s** | 1.6132 s | 1.6755 s | Mean RTF 0.1804 |
| Full voice request | 3/3 | **32.5907 s** | 32.4552 s | 32.8109 s | Transcript matched sample |

ASR/E2E input was a 9.088-second synthetic 24 kHz mono WAV. The earlier single end-to-end request took 32.4416 seconds and produced 21.803 seconds of output audio. These are small exploratory measurements, not statistically robust production SLO estimates.

### 8.3 How to reproduce measurements

The archive contains **results**, including `speech_repeated_benchmark.csv`, `speech_benchmark_summary.json`, `final_metrics.csv`, and `final_summary.json`. It does **not** provide a dedicated, standalone benchmark runner script that can be invoked as a normal CLI program. Relevant experiment code may be preserved within `AMD_MI300X_Voice_Agent_Updated_MVP.ipynb`; extract, review and pin such code before publishing reproducibility instructions.

For a proper production study, separately measure warm vs cold requests, per-stage spans, audio length variability, error rate, p50/p95 over a larger sample, sustained duration, request concurrency, and resource usage.

---

## 9. Observability and incident playbook

**Available:** `GET /metrics` via Prometheus client; `voice_agent_requests_total` is incremented in the chat handler (including calls from `/voice`). Health endpoints and Docker container logs are present.

**Not implemented:** dependency-aware readiness probe, detailed model-stage timing spans, centralized tracing/logging, production alert rules.

| Symptom | Investigation | Guidance |
|---|---|---|
| vLLM API unavailable | `docker compose --profile gpu logs --tail=100 llm`; `/v1/models` | Verify ROCm devices, model load, VRAM, and image compatibility |
| Whisper slow | `docker compose logs asr`; inspect Torch/GPU | Current archive specifies CPU Whisper; ~28.8 s per 9.1 s audio in benchmark |
| Kokoro start fails | `docker compose logs tts`; verify model files | Ensure both `.onnx` and `voices-v1.0.bin` exist in `services/tts/models/` |
| API ready but voice fails | `/ready` + direct ASR/TTS/vLLM checks | `/ready` currently checks no dependencies |
| Browser microphone unavailable | Browser console/security context | Use HTTPS or localhost and grant microphone permission |
| RAG responses irrelevant | Inspect `services/api/app/rag.py` | Replace deterministic hash-vector placeholder with a true embedding model |
| Voice request takes tens of seconds | Benchmark individual ASR, LLM, TTS stages | CPU Whisper is the measured primary bottleneck |

---

## 10. Security and operational limitations

Prior to Internet-facing deployment, implement authentication and authorization, HTTPS, network binding controls, request-size/rate limits, timeout and retry policies, consent and retention controls for audio/transcripts, secret management, pinned image/dependency versions, resource ceilings, and dependency-aware readiness probes. Do not expose Qdrant, vLLM, Whisper, or Kokoro directly without considered network protections.

`/ws/realtime/{session_id}` accepts connections and session IDs without authentication in the archived code; session history is in-memory and is not durable or multi-replica-safe. The `/documents` endpoint permits unauthenticated data ingestion if exposed publicly. Current `Router` detects simple intent keywords, but there is no implemented external tool execution, so do not advertise functional search/calculator tools.

**Kubernetes status:** the archive includes only an API deployment starter (`kubernetes/api-deployment.yaml` / `.yml`). It is **not** a full GPU/service/data deployment recipe.

---

## 11. Design decisions and future work

**Implemented choices:** local models, Docker Compose orchestration, Qwen via ROCm vLLM, Whisper Small CPU, Kokoro ONNX, Qdrant client, React HTTP chat and voice, optional FastAPI WebSocket token/sentence-audio stream, and in-memory sessions.

**Future work (not demonstrated):**

1. AMD ROCm-accelerated Whisper and measured speedup without displacing vLLM memory reservations.
2. Real embedding model and validated semantic retrieval quality.
3. Full streaming voice from browser to first audible output; reconnect and cancellation tests.
4. Multi-user load, stage-level latency, CPU/GPU utilization traces, larger WER test suites, and voice quality evaluations.
5. Secure ingress, authentication, persistent sessions, backups, version pinning, and dependency-aware health checks.
6. Full infrastructure-as-code and Kubernetes resources only after deployment validation.

---

## 12. Release checklist

- [ ] Confirm all model licenses and approved distribution methods.
- [ ] Restore the missing `kokoro-v1.0.onnx` to the expected path or document a reproducible download/checksum procedure.
- [ ] Provide a non-secret `.env.example` or correct older setup instructions.
- [ ] Pin production-validated image tags and dependencies; replace `:latest` as appropriate.
- [ ] Exclude `node_modules`, notebooks with secrets, checkpoints, generated artifacts, and unnecessary audio from the public source release.
- [ ] Validate all six services from a clean checkout in an isolated environment.
- [ ] Verify typed chat and microphone-to-audio flow in the actual browser.
- [ ] Confirm all benchmark data and experiment methodology can be retrieved independently.
- [ ] Label the self-hosting/API comparison curves as *illustrative scenario assumptions*, not provider quotes or validated break-even points.
- [ ] Complete security, reliability, resource, and operational tests before using the word “production-ready.”

---

## Appendix A — Exact routes and file references

| Function | Route | Source |
|---|---|---|
| API health | `GET /health` | `services/api/app/main.py` |
| API readiness | `GET /ready` | `services/api/app/main.py` |
| Prometheus metrics | `GET /metrics` | `services/api/app/main.py` |
| Document ingest | `POST /documents` | `services/api/app/main.py` |
| Chat | `POST /chat` | `services/api/app/main.py` |
| Text-to-speech | `POST /tts` | `services/api/app/main.py` |
| Full voice turn | `POST /voice` | `services/api/app/main.py` |
| Token/sentence-audio WebSocket | `/ws/realtime/{session_id}` | `services/api/app/main.py` |
| Transcription | `POST /transcribe` | `services/asr/main.py` |
| Synthesis | `POST /synthesize` | `services/tts/main.py` |
| Browser route rewriting | `/api/*`, `/ws/*` | `services/web/nginx.conf` |
| Browser interaction | React state, recording, playback | `services/web/src/App.tsx` |

## Appendix B — Provenance

This document is grounded in the source archive provided by the project owner and the saved experiments under `benchmarks/`. Archive inspection establishes file presence and source implementation, not that the uploaded snapshot was rebuilt and exercised in a fresh environment. Experimental results are self-reported artifacts and should be described as such in an external publication.

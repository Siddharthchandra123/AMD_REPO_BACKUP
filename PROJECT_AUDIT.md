# Project Snapshot Audit — AMD MI300X Voice AI
**Source:** `project(2).zip` · inspected 24 October 2026  
**Assessment:** Functional prototype with archived benchmark evidence. Not yet fully reproducible from the ZIP alone, and not production hardened.

## Confirmed project footprint

- 6,287 ZIP entries, approximately 53 MiB compressed / 131 MiB uncompressed.
- Docker Compose services: `api`, `llm`, `asr`, `tts`, `qdrant`, `web`.
- Backend API and React UI source present.
- vLLM Qwen configuration with AMD GPU device passthrough present.
- 6 benchmark CSVs and generated consolidated metrics; 2 WAV samples.
- ROCm ASR candidate Dockerfile present, **not wired into active Compose**.

## High-priority findings

| Priority | Finding | Source / evidence | Recommended action |
|---|---|---|---|
| Blocker | Kokoro ONNX model `kokoro-v1.0.onnx` missing from archive; Dockerfile copies `models/` and app expects it at startup | `services/tts/Dockerfile`, `services/tts/main.py`, ZIP file inventory | Provide approved download/checksum instructions or artifact separately before claiming clean deployment |
| Important | `SELF_HOSTED.md` says `cp .env.example .env`, but `.env.example` is absent | `SELF_HOSTED.md`, ZIP inventory | Fix docs / add safe template |
| Important | Qdrant embeddings are deterministic hash vectors, not meaningful semantic embeddings | `services/api/app/rag.py` | Replace with real local embedding service; re-evaluate retrieval quality |
| Important | `GET /ready` returns ready without checking dependencies | `services/api/app/main.py` | Add readiness checks for ASR, TTS, vLLM, Qdrant |
| Important | No authentication / rate limiting on chat, documents, voice, or WebSocket; ports exposed by Compose | `services/api/app/main.py`, `docker-compose.yml` | Keep restricted to trusted network; add auth/TLS/limits before public deployment |
| Important | Voice route uses default session ID while text uses browser UUID, risking conversation crossover | `services/api/app/main.py`, `services/web/src/App.tsx` | Pass a session ID through `/voice` and isolate sessions |
| Important | CPU Whisper Small takes ~28.8 s for 9.1-s sample; no GPU passthrough | `services/asr/Dockerfile`, Compose, benchmark CSV | Explicitly label as CPU baseline; GPU acceleration future scope |
| Important | Browser uses HTTP `/chat`/`/voice`; no `WebSocket` object in React source | `services/web/src/App.tsx` | Describe realtime WebSocket as API capability not current browser path |
| Important | Compose uses floating `:latest` tags | `docker-compose.yml` | Pin validated versions or digests for reproducibility |
| Moderate | `services/web/node_modules/` bundled in source ZIP | Archive inventory | Exclude in release; use package lock and `npm ci` |
| Moderate | `/metrics` reports a request counter but lacks detailed stage metrics | `services/api/app/main.py` | Add histograms and end-to-end tracing |
| Moderate | Kubernetes directory only has an API deployment starter | `kubernetes/` | Do not label as complete Kubernetes deployment |
| Moderate | Routing flags for tools are not executed | `services/api/app/agents.py` | Label as planned intent routing, not agent tool execution |
| Moderate | README / older docs may describe provisional integrations without reflecting latest code | `README.md`, `docs/*`, `PRODUCTION.md` | Consolidate authoritative documentation and mark status |
| Moderate | No standalone benchmark runner script in ZIP | `benchmarks/`, notebook | Extract runner and publish workload configuration for reproduction |

## Verification boundary

This is a **static code and artifact inspection**, not a clean rebuild, live pen test, infrastructure penetration test, complete license check, or validation of vendor economic assumptions. Past conversational test outputs provide evidence of prior working operation, but the ZIP cannot be assumed independently deployable without the missing ONNX file.

## Suggested next iteration

1. Repair the archive's missing model artifact instructions and environment-template mismatch.
2. Add `PLAYBOOK.md` grounded in actual routes and commands.
3. Validate Docker services from a fresh isolated environment.
4. Preserve all prior measured benchmarks and accurately disclose limitations.
5. Address authentication, session isolation, true embeddings, version pinning, and reliability before production claims.

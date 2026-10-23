# Production hardening

## Required before public deployment
1. Pin ROCm, vLLM and model container versions.
2. Add TLS at an ingress/load balancer.
3. Add authentication and authorization.
4. Replace the deterministic placeholder embedding with a real embedding model.
5. Configure a real Kokoro-compatible TTS service.
6. Benchmark ASR and move it to a ROCm-optimized server if required.
7. Add Redis/Postgres for distributed session state.
8. Add OpenTelemetry tracing and centralized logs.
9. Add request limits and quotas.
10. Add GPU scheduling and autoscaling.

## Honest status
The control plane and streaming orchestration are implemented. Exact ASR/TTS model runtime choices are deployment-dependent and therefore exposed as stable service contracts rather than hidden hardcoded assumptions.

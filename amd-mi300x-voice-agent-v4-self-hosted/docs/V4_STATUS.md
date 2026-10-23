# V4 Status

## Implemented
- MI300X-oriented ROCm deployment structure
- vLLM OpenAI-compatible LLM interface
- WebSocket real-time orchestration
- interruption/cancellation protocol
- session history
- sentence chunking
- Qdrant document storage and retrieval interface
- health/readiness/metrics endpoints
- Docker Compose and Kubernetes starter manifests

## Provider contracts
ASR, TTS, and embeddings are isolated behind service contracts. This prevents hidden paid dependencies and lets the deployment use fully local implementations.

## Pipecat
The architecture is Pipecat-ready. A concrete Pipecat transport can be attached to the same ASR/LLM/TTS endpoints without changing the agent layer.

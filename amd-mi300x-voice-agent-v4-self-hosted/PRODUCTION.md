# Pipecat integration

The services in this repository are intentionally transport-independent.

For Pipecat, connect the same model endpoints:

Pipecat transport
→ VAD/turn processor
→ ASR HTTP service
→ OpenAI-compatible vLLM endpoint
→ TTS HTTP service
→ output transport

The WebSocket gateway can remain as the fallback/browser development transport.

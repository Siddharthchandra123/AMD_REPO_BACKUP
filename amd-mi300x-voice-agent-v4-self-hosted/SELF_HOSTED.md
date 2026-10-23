# Fully Self-Hosted Deployment

This project is designed to avoid mandatory paid APIs.

## Local services
- ROCm + AMD MI300X
- vLLM model server
- Local ASR provider
- Local TTS provider
- Qdrant
- FastAPI
- Browser client

## Start
cp .env.example .env
docker compose --profile gpu up --build

## Before first production use
1. Select a compatible ROCm/vLLM image for the host ROCm release.
2. Configure the local ASR implementation.
3. Configure the local Kokoro-compatible TTS implementation.
4. Replace the placeholder embedding implementation with a real local embedding service.
5. Review licenses for the exact models used.

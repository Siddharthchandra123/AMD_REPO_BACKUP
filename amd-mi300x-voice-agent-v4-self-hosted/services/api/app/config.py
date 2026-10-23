from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM running on AMD MI300X
    vllm_base_url: str = "http://llm:8000/v1"
    vllm_model: str = "Qwen/Qwen2.5-3B-Instruct"

    # Vector database
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "voice_knowledge"
    embedding_dim: int = 384

    # Speech services
    asr_provider_url: str = "http://asr:9000"
    tts_provider_url: str = "http://tts:9001"

    # Application
    max_session_history: int = 20
    log_level: str = "INFO"

    # Configuration comes from environment variables.
    # No .env file required.
    model_config = SettingsConfigDict(
        extra="ignore"
    )


settings = Settings()

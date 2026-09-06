"""Centralized configuration loaded from environment / .env file."""

from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(StrEnum):
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Provider switch
    llm_provider: LLMProvider = LLMProvider.OPENROUTER

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "nvidia/nemotron-3.5-lightning:free"

    # Anthropic (direct)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Shared LLM
    llm_max_tokens: int = 2048

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_data"
    chroma_collection: str = "incidents"

    # Ingestion
    incident_data_dir: str = "./data/incidents"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # App
    log_level: str = "INFO"

    @property
    def data_path(self) -> Path:
        return Path(self.incident_data_dir)

    @property
    def chroma_path(self) -> Path:
        return Path(self.chroma_persist_dir)


settings = Settings()

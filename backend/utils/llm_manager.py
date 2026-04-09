from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_environment(override: bool = False) -> None:
    """Load environment variables from common project locations."""
    candidate_env_files = [
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / "backend" / ".env",
    ]
    for env_file in candidate_env_files:
        if env_file.exists():
            load_dotenv(dotenv_path=env_file, override=override)

    # Fallback to default dotenv discovery behavior.
    load_dotenv(override=override)


load_environment()


def _configure_langsmith_from_env() -> None:
    """Enable LangSmith tracing when the required environment variables exist."""
    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "").strip().lower()
    if tracing_enabled in {"1", "true", "yes", "on"}:
        return

    langsmith_key = os.getenv("LANGSMITH_API_KEY", "").strip() or os.getenv("LANGCHAIN_API_KEY", "").strip()
    if not langsmith_key:
        return

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", os.getenv("LANGCHAIN_PROJECT", "vinuni-chat-agent"))
    os.environ.setdefault("LANGCHAIN_API_KEY", langsmith_key)
    endpoint = os.getenv("LANGSMITH_ENDPOINT", "").strip() or os.getenv("LANGCHAIN_ENDPOINT", "").strip()
    if endpoint:
        os.environ.setdefault("LANGCHAIN_ENDPOINT", endpoint)


_configure_langsmith_from_env()

_ENV_KEY_CANDIDATES: tuple[str, ...] = (
    "OPENAI_API_KEYS",
    "openai_api_keys",
    "OPENAI_API_KEY",
    "openai_api_key",
)


@dataclass
class _APIKeyRotator:
    """Thread-safe round-robin API key rotator."""

    keys: List[str]

    def __post_init__(self) -> None:
        if not self.keys:
            raise RuntimeError(
                "No OpenAI API key found. Set OPENAI_API_KEYS or OPENAI_API_KEY in environment."
            )
        self._lock = threading.Lock()
        self._index = 0

    def next_key(self) -> str:
        with self._lock:
            key = self.keys[self._index % len(self.keys)]
            self._index = (self._index + 1) % len(self.keys)
            return key


def _parse_key_string(raw: str) -> List[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def _load_keys_from_env() -> List[str]:
    for var_name in _ENV_KEY_CANDIDATES:
        raw_value = os.getenv(var_name, "").strip()
        if raw_value:
            keys = _parse_key_string(raw_value)
            if keys:
                return keys
    return []


_rotator: Optional[_APIKeyRotator] = None
_rotator_lock = threading.Lock()


def refresh_api_key_pool() -> None:
    """Reload API keys from environment for runtime updates."""
    load_environment(override=True)
    global _rotator
    with _rotator_lock:
        _rotator = _APIKeyRotator(keys=_load_keys_from_env())


def _get_rotator() -> _APIKeyRotator:
    global _rotator
    if _rotator is None:
        with _rotator_lock:
            if _rotator is None:
                _rotator = _APIKeyRotator(keys=_load_keys_from_env())
    return _rotator


def get_llm(model_name: str = "gpt-4o-mini", temperature: float = 0.2) -> ChatOpenAI:
    """Factory for ChatOpenAI with centralized key management."""
    api_key = _get_rotator().next_key()
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        max_retries=2,
        timeout=30,
    )


def get_embeddings(model_name: str = "text-embedding-3-small") -> OpenAIEmbeddings:
    """Factory for OpenAIEmbeddings with centralized key management."""
    api_key = _get_rotator().next_key()
    return OpenAIEmbeddings(model=model_name, api_key=api_key)

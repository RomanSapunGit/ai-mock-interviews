from __future__ import annotations

from dataclasses import dataclass, field
from os import getenv
from typing import TYPE_CHECKING

from dotenv import load_dotenv
load_dotenv()
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

if TYPE_CHECKING:
    from langchain_postgres import PGVector
    from openai import AsyncOpenAI
    from app.ai.embeddings import GeminiEmbeddings

def _get_database_url() -> str:
    url = getenv("DATABASE_URL")
    if not url:
        return "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_mock_interviews"

    # asyncpg doesn't support 'sslmode', but psycopg does.
    # Strip it out here for SQLAlchemy's asyncpg engine.
    if "?sslmode=require" in url:
        url = url.replace("?sslmode=require", "")
    elif "&sslmode=require" in url:
        url = url.replace("&sslmode=require", "")

    # Standardize protocol for asyncpg compatibility
    if "://" in url:
        scheme, rest = url.split("://", 1)
        if scheme in ["postgres", "postgresql"]:
            return f"postgresql+asyncpg://{rest}"
    return url

RAW_DATABASE_URL = _get_database_url()


@dataclass
class DatabaseSettings:
    DATABASE_URL: str = RAW_DATABASE_URL
    ECHO: bool = bool(int(getenv("DB_ECHO", "0")))

    _engine_instance: AsyncEngine | None = None

    def get_engine(self) -> AsyncEngine:
        if self._engine_instance is not None:
            return self._engine_instance

        self._engine_instance = create_async_engine(
            url=self.DATABASE_URL,
            future=True,
            echo=self.ECHO,
        )
        return self._engine_instance


@dataclass
class AppSettings:
    SECRET_KEY: str = getenv("SECRET_KEY", "")
    DEBUG: bool = bool(int(getenv("DEBUG", "0")))

    # LLM_MODEL wins when set; GROQ_MODEL kept as a fallback for existing envs.
    LLM_MODEL: str = getenv("LLM_MODEL", "") or getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    # Cheap model for lightweight in-question calls (intent classification,
    # hints, clarifications, probes, follow-ups) so they don't burn the main
    # model's quota. Served by EvaluatorSettings.fast_client.
    LLM_FAST_MODEL: str = getenv("LLM_FAST_MODEL", "llama-3.1-8b-instant")
    GROQ_WHISPER_MODEL: str = getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
    # Embeddings run on Google's API; the old EMBEDDING_MODEL /
    # EMBEDDING_DIMENSIONS vars are intentionally ignored so stale values in
    # deployment environments can't select an incompatible model.
    GEMINI_API_KEY: str = getenv("GEMINI_API_KEY", "")
    GEMINI_EMBEDDING_MODEL: str = getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    GEMINI_EMBEDDING_DIMENSIONS: int = int(getenv("GEMINI_EMBEDDING_DIMENSIONS", "768"))
    SENTRY_DSN_URL: str = getenv("SENTRY_DSN_URL", "")

    def __post_init__(self) -> None:
        if self.SECRET_KEY in ("", "changeme"):
            if self.DEBUG:
                self.SECRET_KEY = "dev-only-insecure-secret-key"
            else:
                raise RuntimeError(
                    "SECRET_KEY is not configured. Set the SECRET_KEY environment "
                    "variable (or DEBUG=1 for local development)."
                )


@dataclass
class LangChainSettings:
    _embeddings: GeminiEmbeddings | None = field(default=None, init=False, repr=False)
    collection_name: str = "interview_questions"
    _vector_store_instance: PGVector | None = field(default=None, init=False, repr=False)

    @property
    def embeddings(self) -> GeminiEmbeddings:
        if self._embeddings is None:
            from app.ai.embeddings import GeminiEmbeddings
            self._embeddings = GeminiEmbeddings(
                api_key=settings.app.GEMINI_API_KEY,
                model=settings.app.GEMINI_EMBEDDING_MODEL,
                dimensions=settings.app.GEMINI_EMBEDDING_DIMENSIONS,
            )
        return self._embeddings

    @property
    def vector_store(self) -> PGVector:
        if self._vector_store_instance is None:
            from langchain_postgres import PGVector

            # Re-add sslmode for psycopg if it's external (Render)
            conn_str = RAW_DATABASE_URL.replace("+asyncpg", "+psycopg")
            if ".onrender.com" in conn_str and "sslmode=require" not in conn_str:
                conn_str += "?sslmode=require" if "?" not in conn_str else "&sslmode=require"

            self._vector_store_instance = PGVector(
                embeddings=self.embeddings,
                collection_name=self.collection_name,
                connection=conn_str,
                use_jsonb=True,
            )
        return self._vector_store_instance


@dataclass
class EvaluatorSettings:
    GROQ_API_KEY: str = getenv("GROQ_API_KEY", "")
    # Chat LLM (generation, evaluation, hints): any OpenAI-compatible
    # endpoint. Defaults to Groq; to use Gemini instead set
    #   LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
    #   LLM_API_KEY=<gemini key>
    #   LLM_MODEL=gemini-2.5-flash
    # Audio transcription always uses Groq (Whisper has no Gemini-compatible
    # equivalent), hence the separate client below.
    LLM_BASE_URL: str = getenv("LLM_BASE_URL", "") or "https://api.groq.com/openai/v1"
    LLM_API_KEY: str = getenv("LLM_API_KEY", "") or getenv("GROQ_API_KEY", "")
    # Lightweight calls (LLM_FAST_MODEL) default to Groq even when the main
    # client points at Gemini; override both to move them elsewhere.
    LLM_FAST_BASE_URL: str = getenv("LLM_FAST_BASE_URL", "") or "https://api.groq.com/openai/v1"
    LLM_FAST_API_KEY: str = getenv("LLM_FAST_API_KEY", "") or getenv("GROQ_API_KEY", "")
    _client: AsyncOpenAI | None = field(default=None, init=False, repr=False)
    _fast_client: AsyncOpenAI | None = field(default=None, init=False, repr=False)
    _transcription_client: AsyncOpenAI | None = field(default=None, init=False, repr=False)

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.LLM_API_KEY,
                base_url=self.LLM_BASE_URL,
            )
        return self._client

    @property
    def fast_client(self) -> AsyncOpenAI:
        if self._fast_client is None:
            from openai import AsyncOpenAI
            self._fast_client = AsyncOpenAI(
                api_key=self.LLM_FAST_API_KEY,
                base_url=self.LLM_FAST_BASE_URL,
            )
        return self._fast_client

    @property
    def transcription_client(self) -> AsyncOpenAI:
        if self._transcription_client is None:
            from openai import AsyncOpenAI
            self._transcription_client = AsyncOpenAI(
                api_key=self.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
            )
        return self._transcription_client


@dataclass
class Settings:
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    app: AppSettings = field(default_factory=AppSettings)
    lang_chain: LangChainSettings = field(default_factory=LangChainSettings)
    evaluator: EvaluatorSettings = field(default_factory=EvaluatorSettings)

def get_settings() -> Settings:
    return Settings()

settings = get_settings()

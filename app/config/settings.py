from __future__ import annotations

from dataclasses import dataclass, field
from os import getenv
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_huggingface import HuggingFaceEmbeddings

from dotenv import load_dotenv
load_dotenv()
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_postgres import PGVector
    from openai import AsyncOpenAI
    from langchain_huggingface import HuggingFaceEmbeddings

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
    SECRET_KEY: str = getenv("SECRET_KEY", "changeme")
    DEBUG: bool = bool(int(getenv("DEBUG", "0")))

    GROQ_MODEL: str = getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_WHISPER_MODEL: str = getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
    EMBEDDING_MODEL: str = getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_DIMENSIONS: int = int(getenv("EMBEDDING_DIMENSIONS", "384"))
    SENTRY_DSN_URL: str = getenv("SENTRY_DSN_URL", "")


@dataclass
class LangChainSettings:
    _embeddings: HuggingFaceEmbeddings | None = field(default=None, init=False, repr=False)
    collection_name: str = "interview_questions"
    _vector_store_instance: PGVector | None = field(default=None, init=False, repr=False)

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        if self._embeddings is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            self._embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
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
    _client: AsyncOpenAI | None = field(default=None, init=False, repr=False)

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
            )
        return self._client


@dataclass
class Settings:
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    app: AppSettings = field(default_factory=AppSettings)
    lang_chain: LangChainSettings = field(default_factory=LangChainSettings)
    evaluator: EvaluatorSettings = field(default_factory=EvaluatorSettings)

def get_settings() -> Settings:
    return Settings()

settings = get_settings()

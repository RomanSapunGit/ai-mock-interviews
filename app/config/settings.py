from __future__ import annotations

from dataclasses import dataclass, field
from os import getenv
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
from langchain_postgres import PGVector
from openai import AsyncOpenAI

load_dotenv()
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
RAW_DATABASE_URL = getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_mock_interviews")

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

    CORS_ALLOWED_ORIGINS: list[str] = field(
        default_factory=lambda: [
            "http://localhost:5173"
        ]
    )

@dataclass
class LangChainSettings:
    embeddings: HuggingFaceEmbeddings = field(
        default_factory=lambda: HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    )
    collection_name: str = "interview_questions"
    _vector_store_instance: PGVector | None = field(default=None, init=False, repr=False)

    @property
    def vector_store(self) -> PGVector:
        if self._vector_store_instance is None:
            self._vector_store_instance = PGVector(
                embeddings=self.embeddings,
                collection_name=self.collection_name,
                connection=RAW_DATABASE_URL.replace("+asyncpg", "+psycopg"),
                use_jsonb=True,
            )
        return self._vector_store_instance

@dataclass
class EvaluatorSettings:
    GROQ_API_KEY: str = getenv("GROQ_API_KEY", "")
    client = AsyncOpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )

@dataclass
class Settings:
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    app: AppSettings = field(default_factory=AppSettings)
    lang_chain: LangChainSettings = field(default_factory=LangChainSettings)
    evaluator: EvaluatorSettings = field(default_factory=EvaluatorSettings)

def get_settings() -> Settings:
    return Settings()

settings = get_settings()

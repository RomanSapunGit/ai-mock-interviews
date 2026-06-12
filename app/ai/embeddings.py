"""Cloud embeddings backed by Google's Gemini API.

The embedding model runs on Google's side, so the app process carries no
ML runtime — important on small instances (512MB pods OOM'd loading a
local model). Vectors are 768-dim, so anything indexed with the previous
384-dim local model is incompatible (a migration wipes the old tables).
"""
from __future__ import annotations

import math
import time

import httpx
from langchain_core.embeddings import Embeddings

_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
# Gemini's batchEmbedContents accepts at most 100 contents per call.
_MAX_BATCH = 100
_RETRY_STATUSES = {429, 500, 502, 503}


class GeminiEmbeddings(Embeddings):
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        dimensions: int = 768,
        timeout: float = 60.0,
    ):
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured. Question indexing/search "
                "requires a Google AI API key (https://aistudio.google.com/apikey)."
            )
        self._model = model
        self._dimensions = dimensions
        self._client = httpx.Client(
            base_url=_API_BASE,
            headers={"x-goog-api-key": api_key},
            timeout=timeout,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _MAX_BATCH):
            batch = texts[start : start + _MAX_BATCH]
            vectors.extend(self._embed_batch(batch, task_type="RETRIEVAL_DOCUMENT"))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed_batch([text], task_type="RETRIEVAL_QUERY")[0]

    def _embed_batch(self, texts: list[str], task_type: str) -> list[list[float]]:
        payload = {
            "requests": [
                {
                    "model": f"models/{self._model}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": task_type,
                    "outputDimensionality": self._dimensions,
                }
                for text in texts
            ]
        }
        data = self._post_with_retry(payload)
        return [_normalize(item["values"]) for item in data["embeddings"]]

    def _post_with_retry(self, payload: dict, attempts: int = 3) -> dict:
        for attempt in range(attempts):
            response = self._client.post(
                f"/models/{self._model}:batchEmbedContents", json=payload
            )
            if response.status_code in _RETRY_STATUSES and attempt < attempts - 1:
                time.sleep(2**attempt)
                continue
            response.raise_for_status()
            return response.json()
        raise RuntimeError("unreachable")


def _normalize(values: list[float]) -> list[float]:
    # Gemini only L2-normalizes its full-size output; truncated dimensions
    # (like 768) must be normalized client-side for distances to be sane.
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0:
        return values
    return [v / norm for v in values]

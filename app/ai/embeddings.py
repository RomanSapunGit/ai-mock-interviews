"""Lightweight embeddings backed by fastembed (ONNX runtime, no torch).

Uses the same model weights as the previous sentence-transformers setup
(all-MiniLM-L6-v2, 384 dims), so vectors already stored in pgvector remain
compatible.
"""
from __future__ import annotations

from langchain_core.embeddings import Embeddings


class FastEmbedEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        from fastembed import TextEmbedding

        # Single-threaded inference: on fractional-CPU instances (e.g. 0.1
        # vCPU) onnxruntime's default thread pool only adds contention.
        self._model = TextEmbedding(model_name=model_name, threads=1)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

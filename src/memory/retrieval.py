"""Retrieval layer that unifies keyword and optional embedding search."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Sequence

from .models import MemoryEntry, MemoryResult, MemoryType

_TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


def _tokens(text: str) -> Counter[str]:
    return Counter(_TOKEN_PATTERN.findall(text.casefold()))


def _cosine_similarity(query: Counter[str], document: Counter[str]) -> float:
    if not query or not document:
        return 0.0
    dot = sum(count * document.get(token, 0) for token, count in query.items())
    q_norm = math.sqrt(sum(c * c for c in query.values()))
    d_norm = math.sqrt(sum(c * c for c in document.values()))
    return dot / (q_norm * d_norm) if q_norm and d_norm else 0.0


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    """Parameters for a memory retrieval request."""

    text: str
    types: tuple[MemoryType, ...] | None = None
    scope: tuple[str, ...] | None = None
    limit: int = 5
    token_budget: int | None = None
    min_confidence: float = 0.0
    min_importance: float = 0.0


EmbeddingFn = Callable[[str], Sequence[float]]


def _dot_product(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _vector_norm(vec: Sequence[float]) -> float:
    return math.sqrt(sum(x * x for x in vec))


def _cosine_similarity_vectors(a: Sequence[float], b: Sequence[float]) -> float:
    norm_a = _vector_norm(a)
    norm_b = _vector_norm(b)
    if not norm_a or not norm_b:
        return 0.0
    return _dot_product(a, b) / (norm_a * norm_b)


class MemoryRetriever:
    """Unified retrieval interface combining keyword and optional embedding search."""

    def __init__(
        self,
        entries: Sequence[MemoryEntry],
        *,
        embedding_fn: EmbeddingFn | None = None,
        keyword_weight: float = 0.6,
        embedding_weight: float = 0.4,
    ) -> None:
        if not 0.0 <= keyword_weight <= 1.0:
            raise ValueError("keyword_weight must be between 0.0 and 1.0")
        if not 0.0 <= embedding_weight <= 1.0:
            raise ValueError("embedding_weight must be between 0.0 and 1.0")
        self._entries = list(entries)
        self._embedding_fn = embedding_fn
        self._keyword_weight = keyword_weight
        self._embedding_weight = embedding_weight
        self._entry_keyword_vectors: dict[str, Counter[str]] = {
            entry.id: _tokens(entry.text) for entry in self._entries
        }
        self._entry_embeddings: dict[str, tuple[float, ...]] | None = None
        if embedding_fn is not None:
            self._entry_embeddings = {
                entry.id: tuple(embedding_fn(entry.text)) for entry in self._entries
            }

    def search(self, query: RetrievalQuery) -> list[MemoryResult]:
        """Return ranked memories matching the query within optional token budget."""
        candidates = self._filter(query)
        if not candidates:
            return []

        query_keywords = _tokens(query.text)
        query_embeddings = None
        if self._embedding_fn is not None and self._entry_embeddings is not None:
            query_embeddings = tuple(self._embedding_fn(query.text))

        scored: list[MemoryResult] = []
        for entry in candidates:
            keyword_score = _cosine_similarity(query_keywords, self._entry_keyword_vectors[entry.id])
            embedding_score = 0.0
            if query_embeddings is not None and self._entry_embeddings is not None:
                entry_vec = self._entry_embeddings.get(entry.id)
                if entry_vec:
                    embedding_score = _cosine_similarity_vectors(query_embeddings, entry_vec)
            score = (
                self._keyword_weight * keyword_score
                + self._embedding_weight * embedding_score
            )
            scored.append(MemoryResult(entry=entry, score=score, retrieval_path="keyword" if query_embeddings is None else "hybrid"))

        scored.sort(key=lambda result: (result.score, result.entry.created_at), reverse=True)
        scored = [r for r in scored if r.score > 0.0]
        return self._apply_token_budget(scored, query.token_budget or 0)[: query.limit]

    def _filter(self, query: RetrievalQuery) -> list[MemoryEntry]:
        filtered = []
        for entry in self._entries:
            if query.types is not None and entry.memory_type not in query.types:
                continue
            if query.scope is not None and entry.scope not in query.scope:
                continue
            if entry.confidence < query.min_confidence:
                continue
            if entry.importance < query.min_importance:
                continue
            filtered.append(entry)
        return filtered

    def _apply_token_budget(self, results: list[MemoryResult], token_budget: int) -> list[MemoryResult]:
        if not token_budget or token_budget <= 0:
            return results
        budgeted: list[MemoryResult] = []
        used = 0
        for result in results:
            tokens = len(_TOKEN_PATTERN.findall(result.entry.text))
            if used + tokens > token_budget:
                break
            budgeted.append(result)
            used += tokens
        return budgeted

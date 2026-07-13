"""Memory manager with promotion, consolidation, contradiction handling, and retention."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from .models import (
    DEFAULT_RETENTION,
    ContradictionRecord,
    MemoryEntry,
    MemoryScope,
    MemorySource,
    MemorySummary,
    MemoryType,
    RetentionPolicy,
    SensitivityLevel,
)
from .store import MemoryStore
from .retrieval import MemoryRetriever, RetrievalQuery

logger = logging.getLogger(__name__)


class MemoryManager:
    """Decides what is promoted, consolidated, and retained."""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def add_working_memory(
        self,
        text: str,
        *,
        source: MemorySource = MemorySource.ASSISTANT_INFERRED,
        confidence: float = 0.7,
        importance: float = 0.6,
        sensitivity: SensitivityLevel = SensitivityLevel.LOW,
        scope: MemoryScope = MemoryScope.SESSION,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Store short-lived working memory and return the entry."""
        return self.store.add(
            text,
            memory_type=MemoryType.WORKING,
            source=source,
            confidence=confidence,
            importance=importance,
            sensitivity=sensitivity,
            scope=scope,
            metadata=metadata,
        )

    def promote_to_long_term(self, entry_id: str) -> MemoryEntry | None:
        """Promote a working memory to an appropriate long-term type."""
        with self.store._lock:
            for entry in self.store._entries:
                if entry.id == entry_id:
                    if entry.memory_type != MemoryType.WORKING:
                        return None
                    promoted = MemoryEntry(
                        id=entry.id,
                        memory_type=MemoryType.EPISODIC,
                        text=entry.text,
                        source=entry.source,
                        confidence=entry.confidence,
                        importance=entry.importance,
                        sensitivity=entry.sensitivity,
                        scope=entry.scope,
                        created_at=entry.created_at,
                        updated_at=datetime.now(timezone.utc).isoformat(),
                        metadata=dict(entry.metadata),
                        supersedes=entry.supersedes,
                        summary_of=entry.summary_of,
                    )
                    idx = self.store._entries.index(entry)
                    self.store._entries[idx] = promoted
                    self.store.save()
                    return promoted
        return None

    def consolidate_duplicates(self) -> list[MemoryEntry]:
        """Merge near-duplicate entries and return the survivors."""
        seen_texts: dict[str, MemoryEntry] = {}
        superseded: list[MemoryEntry] = []
        with self.store._lock:
            for entry in self.store._entries:
                normalized = entry.text.casefold().strip()
                if normalized in seen_texts:
                    existing = seen_texts[normalized]
                    if entry.importance > existing.importance:
                        seen_texts[normalized] = entry
                        superseded.append(existing)
                    else:
                        superseded.append(entry)
                else:
                    seen_texts[normalized] = entry
            if superseded:
                keep_ids = {entry.id for entry in seen_texts.values()}
                self.store._entries = [
                    entry for entry in self.store._entries if entry.id in keep_ids
                ]
                self.store.save()
        return list(seen_texts.values())

    def handle_contradiction(
        self, existing: MemoryEntry, incoming: MemoryEntry
    ) -> ContradictionRecord | None:
        """Detect and resolve contradictions between memories."""
        if existing.text.casefold().strip() == incoming.text.casefold().strip():
            return None
        resolution = "keep_existing"
        if incoming.confidence > existing.confidence:
            resolution = "supersede"
            with self.store._lock:
                for idx, entry in enumerate(self.store._entries):
                    if entry.id == existing.id:
                        updated = MemoryEntry(
                            id=entry.id,
                            memory_type=entry.memory_type,
                            text=entry.text,
                            source=entry.source,
                            confidence=entry.confidence,
                            importance=entry.importance,
                            sensitivity=entry.sensitivity,
                            scope=entry.scope,
                            created_at=entry.created_at,
                            updated_at=datetime.now(timezone.utc).isoformat(),
                            metadata=dict(entry.metadata),
                            supersedes=incoming.id,
                            summary_of=entry.summary_of,
                        )
                        self.store._entries[idx] = updated
                        self.store.save()
                        break
        elif incoming.importance > existing.importance:
            resolution = "keep_existing_but_note"
        record = ContradictionRecord(
            existing_id=existing.id,
            incoming_id=incoming.id,
            existing_text=existing.text,
            incoming_text=incoming.text,
            resolution=resolution,
            resolved_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.debug("Contradiction resolved: %s", record)
        return record

    def summarize(
        self, source_ids: tuple[str, ...], summary_text: str
    ) -> MemorySummary | None:
        """Create a procedural summary that references the original memories."""
        entries = [e for e in self.store.entries if e.id in source_ids]
        if not entries:
            return None
        avg_importance = sum(e.importance for e in entries) / len(entries)
        avg_confidence = sum(e.confidence for e in entries) / len(entries)
        memory_type = entries[0].memory_type
        now = datetime.now(timezone.utc).isoformat()
        summary = MemorySummary(
            id=self.store.add(
                summary_text,
                memory_type=MemoryType.PROCEDURAL,
                source=MemorySource.ASSISTANT_INFERRED,
                confidence=avg_confidence,
                importance=avg_importance,
                sensitivity=SensitivityLevel.LOW,
                scope=entries[0].scope,
                metadata={"summary_of": list(source_ids)},
            ).id,
            summary_text=summary_text,
            source_ids=source_ids,
            memory_type=memory_type,
            created_at=now,
            importance=avg_importance,
            confidence=avg_confidence,
        )
        return summary

    def apply_retention(self, policy: RetentionPolicy | None = None) -> int:
        """Apply retention policy; returns number of removed entries."""
        policy = policy or RetentionPolicy()
        removed = 0
        with self.store._lock:
            before = len(self.store._entries)
            cutoff = None
            if policy.max_age_days is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=policy.max_age_days)
            kept = []
            for entry in self.store._entries:
                if cutoff is not None and datetime.fromisoformat(entry.created_at) < cutoff:
                    removed += 1
                    continue
                if entry.confidence < policy.min_confidence:
                    removed += 1
                    continue
                kept.append(entry)
            kept.sort(key=lambda e: (e.importance, e.created_at), reverse=True)
            if policy.max_entries is not None:
                kept = kept[: policy.max_entries]
                removed += max(0, len(kept) - policy.max_entries)
            self.store._entries = kept
            if removed:
                self.store.save()
        return removed

    def build_retriever(
        self,
        *,
        embedding_fn: any = None,
        keyword_weight: float = 0.6,
        embedding_weight: float = 0.4,
    ) -> MemoryRetriever:
        """Build a retriever over current store entries."""
        return MemoryRetriever(
            self.store.entries,
            embedding_fn=embedding_fn,
            keyword_weight=keyword_weight,
            embedding_weight=embedding_weight,
        )

    def retrieve(
        self,
        query: RetrievalQuery,
        *,
        embedding_fn: any = None,
    ) -> list[MemoryResult]:
        """Retrieve memories matching the query."""
        retriever = self.build_retriever(embedding_fn=embedding_fn)
        return retriever.search(query)

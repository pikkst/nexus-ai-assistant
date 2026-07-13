"""Memory manager with promotion, consolidation, contradiction handling, and retention."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Sequence

from .models import (
    ConsentAction,
    ConsentPolicy,
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
from .retrieval import EmbeddingFn, MemoryRetriever, RetrievalQuery
from .store import MemoryStore

logger = logging.getLogger(__name__)


class MemoryManager:
    """Decides what is promoted, consolidated, and retained."""

    def __init__(self, store: MemoryStore, consent_policy: ConsentPolicy | None = None) -> None:
        self.store = store
        self.consent_policy = consent_policy or ConsentPolicy()

    def _check_consent(self, sensitivity: SensitivityLevel, text: str) -> bool:
        if self.consent_policy.action == ConsentAction.NEVER_STORE:
            return False
        if self.consent_policy.action == ConsentAction.ALLOW:
            return True
        if self.store.contains_sensitive(text, self.consent_policy):
            return False
        return True

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
    ) -> MemoryEntry | None:
        """Store short-lived working memory and return the entry, or None if consent denied."""
        if not self._check_consent(sensitivity, text):
            logger.debug("Consent denied for working memory: %s", text[:100])
            return None
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
                        pinned=entry.pinned,
                    )
                    idx = self.store._entries.index(entry)
                    self.store._entries[idx] = promoted
                    self.store._record_audit("promote", entry_id)
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
                            pinned=entry.pinned,
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
                pre_slice = len(kept)
                kept = kept[: policy.max_entries]
                removed += max(0, pre_slice - policy.max_entries)
            self.store._entries = kept
            if removed:
                self.store.save()
        return removed

    def build_retriever(
        self,
        *,
        embedding_fn: EmbeddingFn | None = None,
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
        embedding_fn: EmbeddingFn | None = None,
    ) -> list[MemoryResult]:
        """Retrieve memories matching the query."""
        retriever = self.build_retriever(embedding_fn=embedding_fn)
        return retriever.search(query)

    def search(
        self,
        *,
        query_text: str = "",
        types: tuple[MemoryType, ...] | None = None,
        scope_filter: tuple[str, ...] | None = None,
        source_filter: tuple[str, ...] | None = None,
        sensitivity_filter: tuple[str, ...] | None = None,
        limit: int = 50,
    ) -> list[MemoryEntry]:
        """Search memories with optional filters, returning MemoryEntry objects."""
        if query_text:
            type_values = types
            scope_values = tuple(MemoryScope(s) for s in scope_filter) if scope_filter else None
            query = RetrievalQuery(
                text=query_text,
                types=type_values,
                scope=scope_values,
                limit=limit,
            )
            results = self.retrieve(query)
            entries = [r.entry for r in results]
        else:
            entries = list(self.store.entries)

        if types:
            entries = [e for e in entries if e.memory_type in types]
        if scope_filter:
            scopes = {MemoryScope(s) for s in scope_filter}
            entries = [e for e in entries if e.scope in scopes]
        if source_filter:
            sources = {MemorySource(s) for s in source_filter}
            entries = [e for e in entries if e.source in sources]
        if sensitivity_filter:
            sensitivities = {SensitivityLevel(s) for s in sensitivity_filter}
            entries = [e for e in entries if e.sensitivity in sensitivities]
        return entries[:limit]

    def delete_memory(self, entry_id: str) -> MemoryEntry | None:
        """Delete a memory by ID. Returns the deleted entry or None."""
        return self.store.delete(entry_id)

    def update_memory(self, entry_id: str, new_text: str) -> MemoryEntry | None:
        """Update the text of a memory by ID. Returns the updated entry or None."""
        return self.store.update_text(entry_id, new_text)

    def toggle_pin(self, entry_id: str) -> MemoryEntry | None:
        """Toggle the pinned state of a memory by ID."""
        return self.store.toggle_pin(entry_id)

    def export_by_type(self, memory_type: MemoryType) -> str:
        """Export memories of a given type as JSON string."""
        return self.store.export_by_type(memory_type)

    def export_by_scope(self, scope: MemoryScope) -> str:
        """Export memories of a given scope as JSON string."""
        return self.store.export_by_scope(scope)

    def export_by_time_range(self, start: datetime, end: datetime) -> str:
        """Export memories within a time range as JSON string."""
        return self.store.export_by_time_range(start, end)

    def clear_by_type(self, memory_type: MemoryType) -> int:
        """Delete all memories of a given type. Returns count removed."""
        return self.store.clear_by_type(memory_type)

    def clear_by_scope(self, scope: MemoryScope) -> int:
        """Delete all memories of a given scope. Returns count removed."""
        return self.store.clear_by_scope(scope)

    def clear_by_time_range(self, start: datetime, end: datetime) -> int:
        """Delete all memories within a time range. Returns count removed."""
        return self.store.clear_by_time_range(start, end)

    def generate_self_summary(self, query: str = "user preferences and facts") -> str:
        """Generate a human-readable summary answering 'What do you remember about me?'."""
        retriever = self.build_retriever()
        results = retriever.search(RetrievalQuery(query, limit=20))
        if not results:
            return "I don't have any memories stored yet."
        lines = ["Here is what I remember about you:\n"]
        for result in results:
            entry = result.entry
            lines.append(f"- [{entry.memory_type.value}] {entry.text}")
        return "\n".join(lines)

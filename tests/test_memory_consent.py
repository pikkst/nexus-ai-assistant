"""Tests for the Memory Consent & Management UI (MEM-003)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.config.settings import NexusConfig
from src.memory import (
    ConsentAction,
    ConsentPolicy,
    MemoryAuditRecord,
    MemoryEntry,
    MemoryManager,
    MemoryScope,
    MemorySource,
    MemoryStore,
    MemoryType,
    SensitivityLevel,
)


def test_store_delete_removes_entry(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    entry = store.add("Temporary thought", memory_type=MemoryType.WORKING)
    assert entry.id in [e.id for e in store.entries]
    removed = store.delete(entry.id)
    assert removed is not None
    assert removed.id == entry.id
    assert entry.id not in [e.id for e in store.entries]


def test_store_delete_missing_returns_none(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    assert store.delete("nonexistent-id") is None


def test_store_update_text_changes_content(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    entry = store.add("Original text")
    updated = store.update_text(entry.id, "Updated text")
    assert updated is not None
    assert updated.text == "Updated text"
    assert updated.updated_at != entry.created_at
    reloaded = MemoryStore(tmp_path)
    assert reloaded.entries[0].text == "Updated text"


def test_store_update_text_empty_raises(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    entry = store.add("Original text")
    with pytest.raises(ValueError, match="cannot be empty"):
        store.update_text(entry.id, "   ")


def test_store_toggle_pin_changes_state(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    entry = store.add("Pinnable memory")
    assert entry.pinned is False
    toggled = store.toggle_pin(entry.id)
    assert toggled is not None
    assert toggled.pinned is True
    toggled_again = store.toggle_pin(entry.id)
    assert toggled_again is not None
    assert toggled_again.pinned is False


def test_store_audit_records_add_and_delete(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    entry = store.add("Audited memory")
    records = store.audit_log
    assert any(r.action == "add" and r.entry_id == entry.id for r in records)
    store.delete(entry.id)
    records = store.audit_log
    assert any(r.action == "delete" and r.entry_id == entry.id for r in records)


def test_store_export_by_type_returns_json(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.add("Pref A", memory_type=MemoryType.PREFERENCE)
    store.add("Pref B", memory_type=MemoryType.PREFERENCE)
    store.add("Episodic event", memory_type=MemoryType.EPISODIC)
    exported = store.export_by_type(MemoryType.PREFERENCE)
    data = json.loads(exported)
    assert data["memory_type"] == "preference"
    assert len(data["entries"]) == 2


def test_store_export_by_scope_returns_json(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.add("Global fact", scope=MemoryScope.GLOBAL)
    store.add("Project note", scope=MemoryScope.PROJECT)
    exported = store.export_by_scope(MemoryScope.GLOBAL)
    data = json.loads(exported)
    assert data["scope"] == "global"
    assert len(data["entries"]) == 1


def test_store_export_by_time_range(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    now = datetime.now(timezone.utc)
    old_entry = store.add(
        "Old memory",
        created_at=now - timedelta(days=30),
        persist=False,
    )
    new_entry = store.add(
        "New memory",
        created_at=now,
        persist=False,
    )
    exported = store.export_by_time_range(now - timedelta(days=10), now + timedelta(days=1))
    data = json.loads(exported)
    texts = [e["text"] for e in data["entries"]]
    assert "New memory" in texts
    assert "Old memory" not in texts


def test_store_clear_by_type_removes_memories(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.add("Pref A", memory_type=MemoryType.PREFERENCE)
    store.add("Pref B", memory_type=MemoryType.PREFERENCE)
    store.add("Episodic", memory_type=MemoryType.EPISODIC)
    removed = store.clear_by_type(MemoryType.PREFERENCE)
    assert removed == 2
    remaining = store.entries
    assert all(e.memory_type != MemoryType.PREFERENCE for e in remaining)
    assert len(remaining) == 1


def test_store_clear_by_scope_removes_memories(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.add("Global A", scope=MemoryScope.GLOBAL)
    store.add("Global B", scope=MemoryScope.GLOBAL)
    store.add("Project", scope=MemoryScope.PROJECT)
    removed = store.clear_by_scope(MemoryScope.GLOBAL)
    assert removed == 2
    remaining = store.entries
    assert all(e.scope != MemoryScope.GLOBAL for e in remaining)


def test_store_check_consent_ask_policy(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    policy = ConsentPolicy(action=ConsentAction.ASK)
    assert store.check_consent(SensitivityLevel.LOW, policy) is True


def test_store_check_consent_never_store_policy(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    policy = ConsentPolicy(action=ConsentAction.NEVER_STORE)
    assert store.check_consent(SensitivityLevel.HIGH, policy) is False


def test_store_check_consent_allow_policy(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    policy = ConsentPolicy(action=ConsentAction.ALLOW)
    assert store.check_consent(SensitivityLevel.HIGH, policy) is True


def test_store_contains_sensitive_detects_keyword(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    policy = ConsentPolicy(action=ConsentAction.ASK)
    assert store.contains_sensitive("My password is secret123", policy) is True
    assert store.contains_sensitive("I like coffee", policy) is False


def test_manager_consent_denies_never_store(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    policy = ConsentPolicy(action=ConsentAction.NEVER_STORE)
    manager = MemoryManager(store, consent_policy=policy)
    result = manager.add_working_memory("Some thought")
    assert result is None


def test_manager_search_with_filters(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    manager = MemoryManager(store)
    store.add("Pref A", memory_type=MemoryType.PREFERENCE, scope=MemoryScope.GLOBAL)
    store.add("Pref B", memory_type=MemoryType.PREFERENCE, scope=MemoryScope.PROJECT)
    store.add("Episodic event", memory_type=MemoryType.EPISODIC, scope=MemoryScope.SESSION)

    results = manager.search(types=(MemoryType.PREFERENCE,))
    assert len(results) == 2
    assert all(e.memory_type == MemoryType.PREFERENCE for e in results)

    results = manager.search(scope_filter=("global",))
    assert len(results) == 1
    assert results[0].scope == MemoryScope.GLOBAL


def test_manager_generate_self_summary(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    manager = MemoryManager(store)
    store.add("User likes dark mode", memory_type=MemoryType.PREFERENCE)
    store.add("User prefers morning meetings", memory_type=MemoryType.PREFERENCE)
    summary = manager.generate_self_summary()
    assert "dark mode" in summary
    assert "morning meetings" in summary


def test_manager_generate_self_summary_empty(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    manager = MemoryManager(store)
    summary = manager.generate_self_summary()
    assert "don't have any memories" in summary


def test_manager_toggle_pin_and_export(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    manager = MemoryManager(store)
    entry = store.add("Pinnable memory")
    assert manager.toggle_pin(entry.id) is not None
    assert store.entries[0].pinned is True
    exported = manager.export_by_type(entry.memory_type)
    data = json.loads(exported)
    assert len(data["entries"]) == 1


def test_manager_clear_by_scope(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    manager = MemoryManager(store)
    store.add("Global A", scope=MemoryScope.GLOBAL)
    store.add("Global B", scope=MemoryScope.GLOBAL)
    removed = manager.clear_by_scope(MemoryScope.GLOBAL)
    assert removed == 2
    assert len(store.entries) == 0


def test_memory_consent_module_imports() -> None:
    from src.ui import memory_consent

    assert hasattr(memory_consent, "MemoryConsentWindow")
    assert hasattr(memory_consent, "open_memory_consent")


def test_store_pinned_survives_persistence(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    entry = store.add("Pinned memory")
    store.toggle_pin(entry.id)
    reloaded = MemoryStore(tmp_path)
    assert reloaded.entries[0].pinned is True


def test_store_legacy_loads_with_pinned_default(tmp_path: Path) -> None:
    legacy_path = tmp_path / "legacy.json"
    legacy_payload = {
        "version": 1,
        "entries": [
            {
                "id": "legacy-1",
                "text": "Old style memory",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {},
            }
        ],
    }
    legacy_path.write_text(json.dumps(legacy_payload), encoding="utf-8")
    store = MemoryStore(legacy_path)
    assert store.entries[0].pinned is False


def test_manager_search_by_source_filter(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    manager = MemoryManager(store)
    store.add("User fact", source=MemorySource.USER_STATED)
    store.add("Assistant fact", source=MemorySource.ASSISTANT_INFERRED)
    results = manager.search(source_filter=("user_stated",))
    assert len(results) == 1
    assert results[0].source == MemorySource.USER_STATED


def test_manager_search_by_sensitivity_filter(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    manager = MemoryManager(store)
    store.add("Low sens", sensitivity=SensitivityLevel.LOW)
    store.add("High sens", sensitivity=SensitivityLevel.HIGH)
    results = manager.search(sensitivity_filter=("high",))
    assert len(results) == 1
    assert results[0].sensitivity == SensitivityLevel.HIGH

"""Evaluation layer tests for result verification, feedback, and metrics."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.eval import (
    EvalMetrics,
    EvalStore,
    FeedbackCollector,
    FeedbackKind,
    MetricsTracker,
    StepVerifier,
    SuccessCriterion,
    VerificationResult,
)
from src.eval.models import CriterionResult, EvaluationRecord, FeedbackSignal
from src.tasks import (
    Evidence,
    GoalStatus,
    PlanStep,
    StepStatus,
    TaskManager,
    TaskStore,
    TaskStateError,
)


def verified(summary: str = "ok") -> Evidence:
    return Evidence("test", summary, verified=True)


def machine_criterion(cid: str, description: str, expression: str | None = None) -> SuccessCriterion:
    return SuccessCriterion(id=cid, description=description, check_type="machine", expression=expression)


def user_criterion(cid: str, description: str) -> SuccessCriterion:
    return SuccessCriterion(id=cid, description=description, check_type="user_confirmed")


def manager(tmp_path: Path) -> TaskManager:
    return TaskManager(TaskStore(tmp_path / "tasks.json"))


# AC-1: Task steps can define machine-checkable or user-confirmed success criteria
def test_step_can_define_success_criteria(tmp_path: Path) -> None:
    tasks = manager(tmp_path)
    goal = tasks.create_goal("Verified work")
    criteria = [
        machine_criterion("c1", "tests pass", expression="test"),
        user_criterion("c2", "user approves"),
    ]
    step = tasks.add_step(goal.id, "Implement", success_criteria=criteria)
    loaded = tasks.get_goal(goal.id)
    assert len(loaded.steps[0].success_criteria) == 2
    assert loaded.steps[0].success_criteria[0].check_type == "machine"
    assert loaded.steps[0].success_criteria[1].check_type == "user_confirmed"


# AC-2: Verification results include evidence, confidence, and failure explanation
def test_verification_includes_evidence_confidence_and_explanation(tmp_path: Path) -> None:
    verifier = StepVerifier()
    step = PlanStep(
        title="Write tests",
        success_criteria=[machine_criterion("c1", "tests pass", expression="test")],
    )
    result = verifier.verify(step, (verified("pytest"),))
    assert result.passed is True
    assert result.confidence > 0.0
    assert len(result.criteria_results) == 1
    assert result.criteria_results[0].passed is True

    failed = verifier.verify(step, ())
    assert failed.passed is False
    assert failed.failure_explanation != ""


# AC-3: Failed verification returns work to an actionable state
def test_failed_step_can_be_reverted_for_rework(tmp_path: Path) -> None:
    tasks = manager(tmp_path)
    goal = tasks.create_goal("Reworkable work")
    step = tasks.add_step(goal.id, "Do thing")
    tasks.start_goal(goal.id)
    tasks.start_step(goal.id, step.id)
    tasks.fail_step(goal.id, step.id, "Missing evidence")
    assert tasks.get_goal(goal.id).steps[0].status is StepStatus.FAILED
    tasks.revert_step_for_rework(goal.id, step.id)
    reverted = tasks.get_goal(goal.id)
    assert reverted.steps[0].status is StepStatus.PENDING
    assert reverted.steps[0].result is None
    assert reverted.status is GoalStatus.PAUSED


def test_revert_non_failed_step_raises(tmp_path: Path) -> None:
    tasks = manager(tmp_path)
    goal = tasks.create_goal("Rework guard")
    step = tasks.add_step(goal.id, "Do thing")
    tasks.start_goal(goal.id)
    tasks.start_step(goal.id, step.id)
    with pytest.raises(TaskStateError):
        tasks.revert_step_for_rework(goal.id, step.id)


# AC-4: User feedback supports positive, negative, and explanatory signals
def test_feedback_supports_positive_negative_explanatory(tmp_path: Path) -> None:
    collector = FeedbackCollector()
    collector.collect_kind(FeedbackKind.POSITIVE, "Great work", rating=1.0)
    collector.collect_kind(FeedbackKind.NEGATIVE, "Missed edge case", rating=0.2)
    collector.collect_kind(FeedbackKind.EXPLANATORY, "Because of X")
    summary = collector.summary()
    assert summary["counts"]["positive"] == 1
    assert summary["counts"]["negative"] == 1
    assert summary["counts"]["explanatory"] == 1
    assert summary["average_rating"] == pytest.approx(0.6)


# AC-5: Local metrics track success, corrections, latency, and memory usefulness
def test_metrics_track_success_corrections_latency_and_memory(tmp_path: Path) -> None:
    tracker = MetricsTracker()
    tracker.record_verification(True, 120.0)
    tracker.record_verification(False, 80.0)
    tracker.record_correction()
    tracker.record_memory_usefulness(0.8)
    tracker.record_memory_usefulness(0.4)
    metrics = tracker.snapshot()
    assert metrics.total_evaluations == 2
    assert metrics.successful_verifications == 1
    assert metrics.failed_verifications == 1
    assert metrics.corrections == 1
    assert metrics.average_latency_ms == pytest.approx(100.0)
    assert metrics.average_memory_usefulness == pytest.approx(0.6)
    assert metrics.success_rate == pytest.approx(0.5)


# AC-6: Tests prove that unsupported completion claims are rejected
def test_completion_without_verified_evidence_is_rejected(tmp_path: Path) -> None:
    tasks = manager(tmp_path)
    goal = tasks.create_goal("Needs evidence")
    step = tasks.add_step(goal.id, "Work")
    tasks.start_goal(goal.id)
    tasks.start_step(goal.id, step.id)
    with pytest.raises(TaskStateError, match="Verified evidence"):
        tasks.complete_step(goal.id, step.id, "Done", [Evidence("raw", "unverified")])


def test_completion_with_verified_evidence_succeeds(tmp_path: Path) -> None:
    tasks = manager(tmp_path)
    goal = tasks.create_goal("Verified work")
    step = tasks.add_step(goal.id, "Work")
    tasks.start_goal(goal.id)
    tasks.start_step(goal.id, step.id)
    tasks.complete_step(goal.id, step.id, "Done", [verified()])
    assert tasks.get_goal(goal.id).steps[0].result is not None
    assert tasks.get_goal(goal.id).steps[0].result.success is True


# Integration: evaluation record persists and loads
def test_eval_store_persists_and_loads(tmp_path: Path) -> None:
    store = EvalStore(tmp_path / "eval.jsonl")
    record = EvaluationRecord(
        goal_id="g1",
        step_id="s1",
        verification=VerificationResult(
            passed=True,
            criteria_results=(CriterionResult("c1", True, "ok"),),
            confidence=0.9,
            failure_explanation="",
        ),
        feedback=FeedbackSignal(kind=FeedbackKind.POSITIVE, message="nice", rating=1.0),
    )
    store.append(record)
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].goal_id == "g1"
    assert loaded[0].verification.passed is True
    assert loaded[0].feedback is not None
    assert loaded[0].feedback.kind is FeedbackKind.POSITIVE


# Integration: verifier drives task completion and rework
def test_verifier_integration_with_task_manager(tmp_path: Path) -> None:
    tasks = manager(tmp_path)
    verifier = StepVerifier()
    goal = tasks.create_goal("Integration")
    step = tasks.add_step(
        goal.id,
        "Ship",
        success_criteria=[machine_criterion("c1", "tests", expression="test")],
    )
    tasks.start_goal(goal.id)
    tasks.start_step(goal.id, step.id)

    evidence = (verified("pytest"),)
    result = verifier.verify(step, evidence)
    assert result.passed is True
    tasks.complete_step(goal.id, step.id, "Verified", evidence)
    tasks.complete_goal(goal.id)
    assert tasks.get_goal(goal.id).status is GoalStatus.COMPLETED

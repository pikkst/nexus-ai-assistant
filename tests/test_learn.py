"""Tests for the safe reflection and learning loop."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.eval import FeedbackKind
from src.eval.models import CriterionResult, EvaluationRecord, FeedbackSignal, VerificationResult
from src.eval.metrics import EvalMetrics
from src.learn import (
    DevReportGenerator,
    ImprovementTarget,
    LessonStore,
    LessonStatus,
    QuarantineManager,
    ReflectionEngine,
    create_learning_layer,
)
from src.learn.models import (
    DevReport,
    ImprovementProposal,
    Lesson,
    QuarantineRecord,
    utc_now,
)
from src.memory import MemoryManager, MemoryStore
from src.tasks import (
    Evidence,
    GoalStatus,
    PlanStep,
    StepStatus,
    TaskManager,
    TaskStore,
)
from src.tasks.models import Goal, SuccessCriterion


def make_eval_record(goal_id: str, step_id: str, passed: bool, confidence: float = 0.9, feedback_kind: FeedbackKind | None = None, feedback_rating: float | None = None) -> EvaluationRecord:
    feedback = None
    if feedback_kind:
        feedback = FeedbackSignal(
            kind=feedback_kind,
            message="test feedback",
            rating=feedback_rating,
        )
    return EvaluationRecord(
        goal_id=goal_id,
        step_id=step_id,
        verification=VerificationResult(
            passed=passed,
            criteria_results=(CriterionResult("c1", passed, "ok"),),
            confidence=confidence,
            failure_explanation="" if passed else "missing evidence",
        ),
        feedback=feedback,
    )


def make_goal(tmp_path: Path, title: str = "Test goal") -> Goal:
    tasks = TaskManager(TaskStore(tmp_path / "tasks.json"))
    goal = tasks.create_goal(title)
    step = tasks.add_step(
        goal.id,
        "Do work",
        success_criteria=[SuccessCriterion(id="c1", description="tests pass", check_type="machine", expression="test")],
    )
    tasks.start_goal(goal.id)
    tasks.start_step(goal.id, step.id)
    return tasks, goal, step


class TestLessonStore:
    def test_append_and_load_lessons(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        lesson = Lesson(
            id="l1",
            text="Lesson text",
            scope="test",
            confidence=0.8,
            provenance=("g1", "s1"),
            expected_benefit="better results",
        )
        store.add_lesson(lesson)
        loaded = store.load_lessons()
        assert len(loaded) == 1
        assert loaded[0].id == "l1"
        assert loaded[0].status is LessonStatus.PENDING

    def test_append_and_load_proposals(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        proposal = ImprovementProposal(
            id="p1",
            lesson_id="l1",
            target=ImprovementTarget.CODE,
            description="improve code",
            proposed_change="refactor",
            rationale="clarity",
        )
        store.add_proposal(proposal)
        loaded = store.load_proposals()
        assert len(loaded) == 1
        assert loaded[0].target is ImprovementTarget.CODE

    def test_append_and_load_quarantine(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        record = QuarantineRecord(
            id="q1",
            lesson_id="l1",
            reason="low_confidence",
            conflicting_lesson_ids=(),
        )
        store.add_quarantine(record)
        loaded = store.load_quarantine()
        assert len(loaded) == 1
        assert loaded[0].reason == "low_confidence"


class TestQuarantineManager:
    def test_low_confidence_lesson_is_quarantined(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        qm = QuarantineManager(store)
        lesson = Lesson(
            id="l1",
            text="dubious",
            scope="test",
            confidence=0.3,
            provenance=(),
            expected_benefit="maybe",
        )
        record = qm.evaluate(lesson, [])
        assert record is not None
        assert record.reason == "low_confidence"
        assert qm.is_quarantined("l1") is True

    def test_high_confidence_lesson_passes(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        qm = QuarantineManager(store)
        lesson = Lesson(
            id="l1",
            text="solid lesson",
            scope="test",
            confidence=0.9,
            provenance=(),
            expected_benefit="clear gain",
        )
        record = qm.evaluate(lesson, [])
        assert record is None
        assert qm.is_quarantined("l1") is False

    def test_conflicting_lesson_is_quarantined(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        qm = QuarantineManager(store)
        existing = Lesson(
            id="l0",
            text="use approach X",
            scope="test",
            confidence=0.9,
            provenance=(),
            expected_benefit="clear gain",
            status=LessonStatus.APPROVED,
        )
        new_lesson = Lesson(
            id="l1",
            text="use approach X",
            scope="test",
            confidence=0.9,
            provenance=(),
            expected_benefit="clear gain",
        )
        record = qm.evaluate(new_lesson, [existing])
        assert record is not None
        assert record.reason == "conflict"
        assert "l0" in record.conflicting_lesson_ids

    def test_release_removes_quarantine(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        qm = QuarantineManager(store)
        lesson = Lesson(
            id="l1",
            text="dubious",
            scope="test",
            confidence=0.3,
            provenance=(),
            expected_benefit="maybe",
        )
        qm.evaluate(lesson, [])
        assert qm.is_quarantined("l1") is True
        qm.release("l1")
        assert qm.is_quarantined("l1") is False


class TestReflectionEngine:
    def test_passed_step_generates_lesson(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        qm = QuarantineManager(store)
        engine = ReflectionEngine(memory_manager=None, lesson_store=store, quarantine=qm)
        tasks, goal, step = make_goal(tmp_path)
        tasks.complete_step(goal.id, step.id, "verified", [Evidence("test", "ok", verified=True)])
        record = make_eval_record(goal.id, step.id, passed=True)
        lessons, proposals = engine.reflect([record], tasks.list_goals())
        assert len(lessons) == 1
        assert lessons[0].status is LessonStatus.PENDING
        assert "completed successfully" in lessons[0].text

    def test_failed_step_generates_correction_lesson(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        qm = QuarantineManager(store)
        engine = ReflectionEngine(memory_manager=None, lesson_store=store, quarantine=qm)
        tasks, goal, step = make_goal(tmp_path)
        record = make_eval_record(goal.id, step.id, passed=False, confidence=0.4)
        lessons, proposals = engine.reflect([record], tasks.list_goals())
        assert len(lessons) == 1
        assert lessons[0].status is LessonStatus.QUARANTINED
        assert lessons[0].confidence < 0.5
        assert "failed verification" in lessons[0].text

    def test_negative_feedback_generates_lesson(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        qm = QuarantineManager(store)
        engine = ReflectionEngine(memory_manager=None, lesson_store=store, quarantine=qm)
        tasks, goal, step = make_goal(tmp_path)
        tasks.complete_step(goal.id, step.id, "verified", [Evidence("test", "ok", verified=True)])
        record = make_eval_record(
            goal.id, step.id, passed=True,
            feedback_kind=FeedbackKind.NEGATIVE, feedback_rating=0.2,
        )
        lessons, proposals = engine.reflect([record], tasks.list_goals())
        assert len(lessons) == 1
        assert "negative feedback" in lessons[0].text

    def test_high_confidence_lessons_generate_proposals(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        qm = QuarantineManager(store)
        engine = ReflectionEngine(memory_manager=None, lesson_store=store, quarantine=qm)
        tasks, goal, step = make_goal(tmp_path)
        tasks.complete_step(goal.id, step.id, "verified", [Evidence("test", "ok", verified=True)])
        record = make_eval_record(goal.id, step.id, passed=True, confidence=0.9)
        lessons, proposals = engine.reflect([record], tasks.list_goals())
        assert len(proposals) == 1
        assert proposals[0].requires_approval is True
        assert proposals[0].status == "pending"

    def test_quarantined_lessons_do_not_generate_proposals(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        qm = QuarantineManager(store)
        engine = ReflectionEngine(memory_manager=None, lesson_store=store, quarantine=qm)
        tasks, goal, step = make_goal(tmp_path)
        record = make_eval_record(goal.id, step.id, passed=False, confidence=0.3)
        lessons, proposals = engine.reflect([record], tasks.list_goals())
        assert len(lessons) == 1
        assert lessons[0].status is LessonStatus.QUARANTINED
        assert len(proposals) == 0

    def test_conflicting_lesson_is_quarantined(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        qm = QuarantineManager(store)
        engine = ReflectionEngine(memory_manager=None, lesson_store=store, quarantine=qm)
        tasks, goal, step = make_goal(tmp_path)
        tasks.complete_step(goal.id, step.id, "verified", [Evidence("test", "ok", verified=True)])
        record = make_eval_record(goal.id, step.id, passed=True)
        lessons, _ = engine.reflect([record], tasks.list_goals())
        assert len(lessons) == 1
        assert lessons[0].status is LessonStatus.PENDING

        record2 = make_eval_record(goal.id, step.id, passed=True)
        lessons2, _ = engine.reflect([record2], tasks.list_goals())
        assert len(lessons2) == 1
        assert lessons2[0].status is LessonStatus.QUARANTINED
        all_lessons = store.load_lessons()
        assert len(all_lessons) == 2


class TestDevReportGenerator:
    def test_generates_summary(self, tmp_path: Path) -> None:
        store = LessonStore(tmp_path / "learning")
        lesson = Lesson(
            id="l1",
            text="lesson",
            scope="test",
            confidence=0.8,
            provenance=(),
            expected_benefit="gain",
            status=LessonStatus.APPROVED,
        )
        store.add_lesson(lesson)
        proposal = ImprovementProposal(
            id="p1",
            lesson_id="l1",
            target=ImprovementTarget.CODE,
            description="improve",
            proposed_change="refactor",
            rationale="clarity",
            status="pending",
        )
        store.add_proposal(proposal)

        metrics = EvalMetrics()
        metrics.total_evaluations = 10
        metrics.successful_verifications = 7
        metrics.failed_verifications = 3

        generator = DevReportGenerator(store, eval_metrics=metrics)
        report = generator.generate()
        assert report.total_evaluations == 10
        assert report.lessons_generated == 1
        assert report.lessons_approved == 1
        assert report.proposals_pending == 1
        assert "Development report" in report.summary


class TestCreateLearningLayer:
    def test_factory_returns_components(self, tmp_path: Path) -> None:
        store, reflection, quarantine = create_learning_layer(tmp_path / "learning")
        assert isinstance(store, LessonStore)
        assert isinstance(reflection, ReflectionEngine)
        assert isinstance(quarantine, QuarantineManager)

"""Construction helper for the evaluation layer."""

from __future__ import annotations

from pathlib import Path

from src.eval.feedback import FeedbackCollector
from src.eval.metrics import MetricsTracker
from src.eval.store import EvalStore
from src.eval.verifier import StepVerifier


def create_eval_layer(path: Path | str = Path("~/.nexus/eval")) -> tuple[StepVerifier, FeedbackCollector, MetricsTracker]:
    store = EvalStore(path)
    return StepVerifier(), FeedbackCollector(), MetricsTracker()

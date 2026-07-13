"""Verification logic for task step success criteria."""

from __future__ import annotations

from src.tasks.models import Evidence, PlanStep, SuccessCriterion
from src.eval.models import (
    CriterionResult,
    VerificationResult,
    utc_now,
)


class StepVerifier:
    """Verify step outcomes against declared success criteria."""

    def verify(
        self,
        step: PlanStep,
        evidence: tuple[Evidence, ...] = (),
    ) -> VerificationResult:
        if not step.success_criteria:
            return VerificationResult(
                passed=False,
                criteria_results=(),
                confidence=0.0,
                failure_explanation="No success criteria defined for this step",
            )

        criteria_results: list[CriterionResult] = []
        all_passed = True
        explanations: list[str] = []

        for criterion in step.success_criteria:
            passed, explanation = self._check_criterion(criterion, evidence)
            criteria_results.append(CriterionResult(criterion.id, passed, explanation))
            if not passed:
                all_passed = False
                explanations.append(explanation)

        confidence = self._compute_confidence(evidence, criteria_results)
        failure_explanation = "; ".join(explanations) if explanations else ""

        return VerificationResult(
            passed=all_passed,
            criteria_results=tuple(criteria_results),
            confidence=confidence,
            failure_explanation=failure_explanation,
            verified_at=utc_now(),
        )

    def _check_criterion(
        self,
        criterion: SuccessCriterion,
        evidence: tuple[Evidence, ...],
    ) -> tuple[bool, str]:
        if criterion.check_type == "user_confirmed":
            for item in evidence:
                if item.kind == "user_confirmation" and item.verified:
                    return True, f"User confirmed: {item.summary}"
            return False, f"Missing user confirmation for: {criterion.description}"

        matching = [
            item for item in evidence
            if item.verified
            and (criterion.expression is None or item.kind == criterion.expression)
        ]
        if not matching:
            return False, f"No verified evidence for: {criterion.description}"
        return True, f"Verified by {len(matching)} evidence item(s): {criterion.description}"

    def _compute_confidence(
        self,
        evidence: tuple[Evidence, ...],
        criteria_results: list[CriterionResult],
    ) -> float:
        if not criteria_results:
            return 0.0
        passed = sum(1 for item in criteria_results if item.passed)
        base = passed / len(criteria_results)
        evidence_bonus = min(len(evidence) * 0.05, 0.2)
        return min(base + evidence_bonus, 1.0)

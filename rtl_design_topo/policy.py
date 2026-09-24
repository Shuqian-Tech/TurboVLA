"""Deterministic ALP gates; agent suggestions never bypass these rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import Decision, DecisionAction, Evaluation, EvaluationStatus

FAILURES = {EvaluationStatus.FAILED, EvaluationStatus.ERROR, EvaluationStatus.TIMEOUT}


class AlpPolicy:
    def decide(self, design_id: str, evaluations: list[Evaluation], required: set[str]) -> Decision:
        latest = {evaluation.evaluator: evaluation for evaluation in evaluations}
        failed = sorted(
            name
            for name, evaluation in latest.items()
            if name in required and evaluation.status in FAILURES
        )
        if failed:
            return Decision(DecisionAction.REPAIR, f"failed evaluators: {', '.join(failed)}", design_id)

        missing = sorted(name for name in required if name not in latest)
        if missing:
            return Decision(
                DecisionAction.CONTINUE,
                "required evidence is incomplete",
                design_id,
                requested_evaluators=tuple(missing),
            )

        skipped = sorted(
            name for name in required if latest[name].status == EvaluationStatus.SKIPPED
        )
        if skipped:
            return Decision(DecisionAction.REPAIR, f"blocked evaluators: {', '.join(skipped)}", design_id)

        if all(latest[name].status == EvaluationStatus.PASSED for name in required):
            return Decision(
                DecisionAction.PROMOTE,
                "all deterministic gates in the selected profile passed",
                design_id,
            )
        return Decision(DecisionAction.STOP, "profile ended in an unsupported state", design_id)


@dataclass(frozen=True)
class AgentDecision:
    action: DecisionAction
    parent_design_id: str
    hypothesis: str
    change_description: str
    evaluations: tuple[str, ...]

    @classmethod
    def validate(cls, payload: dict[str, Any], allowed_evaluators: set[str]) -> AgentDecision:
        action = DecisionAction(payload["action"])
        if action not in {
            DecisionAction.CONTINUE,
            DecisionAction.FORK,
            DecisionAction.REPAIR,
            DecisionAction.STOP,
        }:
            raise ValueError("agent decisions cannot directly promote hardware or emit software feedback")
        evaluations = tuple(payload.get("evaluations", ()))
        unknown = set(evaluations) - allowed_evaluators
        if unknown:
            raise ValueError(f"agent requested unknown evaluators: {sorted(unknown)}")
        return cls(
            action=action,
            parent_design_id=str(payload["parent_design_id"]),
            hypothesis=str(payload.get("hypothesis", "")),
            change_description=str(payload.get("change_description", "")),
            evaluations=evaluations,
        )

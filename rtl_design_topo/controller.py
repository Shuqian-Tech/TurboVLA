"""ALP controller coordinating design lineage, evaluators, and policy."""

from __future__ import annotations

import asyncio
from pathlib import Path

from .artifacts import ArtifactStore
from .evaluators import EvaluatorSpec, ProjectConfig
from .executor import LocalExecutor
from .models import DesignState, Evaluation, EvaluationStatus, Event, new_id, utc_now
from .policy import FAILURES, AlpPolicy
from .repository import SqliteRepository
from .source import capture_source_state, current_revision


class ExplorationController:
    def __init__(self, workspace: Path, config: ProjectConfig) -> None:
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.repository = SqliteRepository(self.workspace / "state.sqlite3")
        self.artifacts = ArtifactStore(self.workspace / "artifacts")
        self.executor = LocalExecutor(config.repo_root, self.workspace, self.artifacts, config.resources)
        self.policy = AlpPolicy()

    def create_design(
        self,
        *,
        source_revision: str,
        hypothesis: str,
        change_description: str,
        parent_design_id: str | None = None,
        constraints: dict | None = None,
        created_by: str = "human",
    ) -> DesignState:
        if parent_design_id is not None:
            self.repository.get_design(parent_design_id)
        design = DesignState.create(
            source_revision=source_revision,
            hypothesis=hypothesis,
            change_description=change_description,
            parent_design_id=parent_design_id,
            constraints=constraints,
            created_by=created_by,
        )
        event = Event.create("DESIGN_CREATED", design.design_id, design.to_dict())
        self.repository.add_design(design, event)
        return design

    async def run_profile(
        self,
        design_id: str,
        profile: str,
        *,
        allow_expensive: bool = False,
    ) -> dict:
        design = self.repository.get_design(design_id)
        self._validate_source_identity(design)
        specs = self.config.specs_for(profile, allow_expensive=allow_expensive)
        pending = set(specs)
        completed: dict[str, Evaluation] = {}
        self.repository.add_event(Event.create("PROFILE_STARTED", design_id, {"profile": profile}))

        while pending:
            blocked = self._blocked(pending, specs, completed)
            for name in blocked:
                evaluation = self._skipped(design_id, specs[name], "dependency did not pass")
                self._record_evaluation(evaluation)
                completed[name] = evaluation
                pending.remove(name)

            ready = self._ready(pending, specs, completed)
            if not ready:
                if pending:
                    if blocked:
                        continue
                    raise RuntimeError(f"evaluator dependency cycle: {sorted(pending)}")
                break
            cheapest = min(specs[name].cost for name in ready)
            batch = sorted(name for name in ready if specs[name].cost == cheapest)
            results = await asyncio.gather(*(self.executor.run(design_id, specs[name]) for name in batch))
            for evaluation in results:
                self._record_evaluation(evaluation)
                completed[evaluation.evaluator] = evaluation
                pending.remove(evaluation.evaluator)

        decision = self.policy.decide(design_id, list(completed.values()), set(specs))
        self.repository.add_event(Event.create("POLICY_DECISION", design_id, decision.to_dict()))
        return {
            "design": design.to_dict(),
            "profile": profile,
            "evaluations": [completed[name].to_dict() for name in specs],
            "decision": decision.to_dict(),
        }

    def _validate_source_identity(self, design: DesignState) -> None:
        expected_state = design.constraints.get("source_state")
        if expected_state is None:
            return
        revision = current_revision(self.config.repo_root)
        if revision != design.source_revision:
            raise RuntimeError(
                f"candidate source revision is {design.source_revision}, current HEAD is {revision}"
            )
        actual_state = capture_source_state(self.config.repo_root, allow_dirty=True)
        if actual_state != expected_state:
            raise RuntimeError("candidate source fingerprint does not match the current working tree")

    @staticmethod
    def _ready(
        pending: set[str], specs: dict[str, EvaluatorSpec], completed: dict[str, Evaluation]
    ) -> set[str]:
        return {
            name
            for name in pending
            if all(
                dependency in completed and completed[dependency].status == EvaluationStatus.PASSED
                for dependency in specs[name].requires
            )
        }

    @staticmethod
    def _blocked(
        pending: set[str], specs: dict[str, EvaluatorSpec], completed: dict[str, Evaluation]
    ) -> set[str]:
        return {
            name
            for name in pending
            if any(
                dependency in completed
                and completed[dependency].status in FAILURES | {EvaluationStatus.SKIPPED}
                for dependency in specs[name].requires
            )
        }

    def _record_evaluation(self, evaluation: Evaluation) -> None:
        event_type = f"EVALUATION_{evaluation.status.value.upper()}"
        event = Event.create(
            event_type,
            evaluation.design_id,
            evaluation.to_dict(),
            evaluation.evaluation_id,
        )
        self.repository.add_evaluation(evaluation, event)

    @staticmethod
    def _skipped(design_id: str, spec: EvaluatorSpec, message: str) -> Evaluation:
        now = utc_now()
        return Evaluation(
            evaluation_id=new_id("evaluation"),
            design_id=design_id,
            evaluator=spec.name,
            phase=spec.phase,
            status=EvaluationStatus.SKIPPED,
            command=spec.command,
            started_at=now,
            finished_at=now,
            duration_seconds=0.0,
            return_code=None,
            message=message,
        )

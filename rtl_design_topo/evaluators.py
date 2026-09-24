"""Configuration-backed evaluator definitions for existing project tools."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import KR260_PART, KR260_PLATFORM


@dataclass(frozen=True)
class EvaluatorSpec:
    name: str
    phase: str
    command: tuple[str, ...]
    cost: int = 1
    requires: tuple[str, ...] = ()
    resource: str = "cpu"
    timeout_seconds: float = 300.0
    environment: dict[str, str] = field(default_factory=dict)
    outputs: tuple[str, ...] = ()
    explicit_only: bool = False


@dataclass(frozen=True)
class ProjectConfig:
    path: Path
    repo_root: Path
    platform: str
    part: str
    resources: dict[str, int]
    profiles: dict[str, tuple[str, ...]]
    evaluators: dict[str, EvaluatorSpec]

    @classmethod
    def load(cls, path: Path) -> ProjectConfig:
        resolved = path.resolve()
        data = json.loads(resolved.read_text(encoding="utf-8"))
        repo_root = (resolved.parent / data.get("repo_root", "..")).resolve()
        platform = data["platform"]
        part = data["part"]
        if platform != KR260_PLATFORM or part != KR260_PART:
            raise ValueError("the exploration MVP only supports AMD Kria KR260/K26")
        evaluators = {
            name: EvaluatorSpec(
                name=name,
                phase=record["phase"],
                command=tuple(record["command"]),
                cost=int(record.get("cost", 1)),
                requires=tuple(record.get("requires", ())),
                resource=record.get("resource", "cpu"),
                timeout_seconds=float(record.get("timeout_seconds", 300)),
                environment=dict(record.get("environment", {})),
                outputs=tuple(record.get("outputs", ())),
                explicit_only=bool(record.get("explicit_only", False)),
            )
            for name, record in data["evaluators"].items()
        }
        profiles = {name: tuple(entries) for name, entries in data["profiles"].items()}
        cls._validate_graph(evaluators, profiles)
        return cls(
            path=resolved,
            repo_root=repo_root,
            platform=platform,
            part=part,
            resources={name: int(count) for name, count in data.get("resources", {"cpu": 1}).items()},
            profiles=profiles,
            evaluators=evaluators,
        )

    @staticmethod
    def _validate_graph(evaluators: dict[str, EvaluatorSpec], profiles: dict[str, tuple[str, ...]]) -> None:
        for evaluator in evaluators.values():
            missing = set(evaluator.requires) - set(evaluators)
            if missing:
                raise ValueError(f"evaluator {evaluator.name} has unknown dependencies: {sorted(missing)}")
        for profile, names in profiles.items():
            missing = set(names) - set(evaluators)
            if missing:
                raise ValueError(f"profile {profile} has unknown evaluators: {sorted(missing)}")
            selected = set(names)
            for name in names:
                outside = set(evaluators[name].requires) - selected
                if outside:
                    raise ValueError(f"profile {profile} omits dependencies for {name}: {sorted(outside)}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                raise ValueError(f"evaluator dependency cycle includes {name}")
            if name in visited:
                return
            visiting.add(name)
            for dependency in evaluators[name].requires:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)

        for name in evaluators:
            visit(name)

    def specs_for(self, profile: str, allow_expensive: bool = False) -> dict[str, EvaluatorSpec]:
        if profile not in self.profiles:
            raise KeyError(f"unknown profile: {profile}")
        specs = {name: self.evaluators[name] for name in self.profiles[profile]}
        restricted = [name for name, spec in specs.items() if spec.explicit_only]
        if restricted and not allow_expensive:
            raise PermissionError(
                f"profile {profile} includes explicit-only evaluators {restricted}; pass --allow-expensive"
            )
        return specs

    def to_summary(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "part": self.part,
            "repo_root": str(self.repo_root),
            "profiles": {name: list(entries) for name, entries in self.profiles.items()},
        }

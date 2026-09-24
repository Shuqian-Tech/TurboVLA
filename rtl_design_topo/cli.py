"""Command-line entry point for the local-first exploration controller."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .controller import ExplorationController
from .evaluators import ProjectConfig
from .source import capture_source_state, current_revision

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "configs" / "rtl_design_topo_minimal.json"


def _json(value: str) -> dict:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("value must be a JSON object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KR260 local-first ALP exploration controller")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="initialize a local exploration workspace")
    init.add_argument("--workspace", type=Path, required=True)

    create = subparsers.add_parser("create", help="create an immutable design candidate")
    create.add_argument("--workspace", type=Path, required=True)
    create.add_argument("--source-revision")
    create.add_argument("--parent-design-id")
    create.add_argument("--hypothesis", required=True)
    create.add_argument("--change-description", required=True)
    create.add_argument("--constraints", type=_json, default={})
    create.add_argument("--created-by", default="human")
    create.add_argument("--allow-dirty", action="store_true")

    fork = subparsers.add_parser("fork", help="create a child of an existing design candidate")
    fork.add_argument("--workspace", type=Path, required=True)
    fork.add_argument("--parent-design-id", required=True)
    fork.add_argument("--source-revision")
    fork.add_argument("--hypothesis", required=True)
    fork.add_argument("--change-description", required=True)
    fork.add_argument("--constraints", type=_json, default={})
    fork.add_argument("--created-by", default="agent")
    fork.add_argument("--allow-dirty", action="store_true")

    run = subparsers.add_parser("run", help="run a configured evaluator profile")
    run.add_argument("--workspace", type=Path, required=True)
    run.add_argument("--design-id", required=True)
    run.add_argument("--profile", default="smoke")
    run.add_argument("--allow-expensive", action="store_true")

    status = subparsers.add_parser("status", help="show design graph and latest evidence")
    status.add_argument("--workspace", type=Path, required=True)
    status.add_argument("--design-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ProjectConfig.load(args.config)
    controller = ExplorationController(args.workspace, config)

    if args.command == "init":
        print(json.dumps({"workspace": str(controller.workspace), "config": config.to_summary()}, indent=2))
        return 0
    if args.command in {"create", "fork"}:
        constraints = dict(args.constraints)
        constraints["source_state"] = capture_source_state(config.repo_root, args.allow_dirty)
        design = controller.create_design(
            source_revision=args.source_revision or current_revision(config.repo_root),
            parent_design_id=getattr(args, "parent_design_id", None),
            hypothesis=args.hypothesis,
            change_description=args.change_description,
            constraints=constraints,
            created_by=args.created_by,
        )
        print(json.dumps(design.to_dict(), indent=2))
        return 0
    if args.command == "run":
        report = asyncio.run(
            controller.run_profile(args.design_id, args.profile, allow_expensive=args.allow_expensive)
        )
        print(json.dumps(report, indent=2))
        return 0 if report["decision"]["action"] == "promote" else 1
    if args.command == "status":
        designs = controller.repository.list_designs()
        if args.design_id:
            designs = [controller.repository.get_design(args.design_id)]
        report = [
            {
                "design": design.to_dict(),
                "latest_statuses": {
                    name: status.value
                    for name, status in controller.repository.latest_statuses(design.design_id).items()
                },
                "events": [event.to_dict() for event in controller.repository.events_for(design.design_id)],
            }
            for design in designs
        ]
        print(json.dumps(report, indent=2))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())

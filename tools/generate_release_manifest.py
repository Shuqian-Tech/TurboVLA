#!/usr/bin/env python3
"""Generate a truthful TurboVLA-Lite task/artifact release manifest."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "docs" / "tasks"
ARTIFACTS = [
    ROOT / "tests" / "data" / "lite_golden" / "golden_tensors.npz",
    ROOT / "tests" / "data" / "lite_parameter_pack_smoke" / "weights.bin",
    ROOT / "tests" / "data" / "lite_parameter_pack_smoke" / "manifest.json",
    ROOT / "tests" / "data" / "lite_replay_report.json",
    ROOT / "tests" / "data" / "lite_stability_report.json",
]


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _task_record(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    status = re.search(r"^- 状态：`([^`]+)`", text, re.MULTILINE)
    branch = re.search(r"^- 分支：`([^`]+)`", text, re.MULTILINE)
    pr = re.search(r"^- PR：([^\n]+)", text, re.MULTILINE)
    return {
        "task": path.stem.split("-", 1)[0],
        "file": str(path.relative_to(ROOT)),
        "status": status.group(1) if status else "unknown",
        "branch": branch.group(1) if branch else None,
        "pr": pr.group(1).strip() if pr else None,
    }


def main() -> int:
    output = ROOT / "docs" / "release" / "turbovla_lite_release_manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    for path in ARTIFACTS:
        if path.exists():
            artifacts[str(path.relative_to(ROOT))] = {
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        else:
            artifacts[str(path.relative_to(ROOT))] = {"status": "missing"}
    tasks = [_task_record(path) for path in sorted(TASK_DIR.glob("T[0-9][0-9][0-9]-*.md"))]
    manifest = {
        "release_status": "blocked_by_acceptance_gates",
        "platform": "kr260-k26",
        "verification_mode": "software_only",
        "hardware_bringup": "not_run",
        "head_commit": _git("rev-parse", "HEAD"),
        "tasks": tasks,
        "artifacts": artifacts,
        "blocking_gates": [
            "independent PRs cannot be pushed by the current GitHub identity",
            "Vivado wrapper points to a missing installation",
            "formal T003 teacher/LIBERO training data and success-rate evaluation are absent",
            "KR260 Hardware Manager/JTAG bring-up is not_run",
        ],
    }
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

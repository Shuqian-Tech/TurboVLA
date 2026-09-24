from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from rtl_design_topo.artifacts import ArtifactStore
from rtl_design_topo.controller import ExplorationController
from rtl_design_topo.evaluators import ProjectConfig
from rtl_design_topo.models import DecisionAction, EvaluationStatus
from rtl_design_topo.policy import AgentDecision
from rtl_design_topo.source import capture_source_state, current_revision


class ExplorationFrameworkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.config_path = self.root / "config.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_config(self, evaluators: dict, profiles: dict | None = None) -> ProjectConfig:
        config = {
            "repo_root": "repo",
            "platform": "kr260-k26",
            "part": "xck26-sfvc784-2LV-c",
            "resources": {"cpu": 2, "vivado": 1},
            "profiles": profiles or {"test": list(evaluators)},
            "evaluators": evaluators,
        }
        self.config_path.write_text(json.dumps(config), encoding="utf-8")
        return ProjectConfig.load(self.config_path)

    def test_design_graph_branches_without_mutating_parent(self) -> None:
        config = self._write_config(
            {"pass": {"phase": "verification", "command": [sys.executable, "-c", "pass"]}}
        )
        controller = ExplorationController(self.root / "workspace", config)
        parent = controller.create_design(
            source_revision="abc123", hypothesis="baseline", change_description="baseline"
        )
        first = controller.create_design(
            source_revision="def456",
            parent_design_id=parent.design_id,
            hypothesis="pipeline",
            change_description="add one stage",
        )
        second = controller.create_design(
            source_revision="fed654",
            parent_design_id=parent.design_id,
            hypothesis="buffer",
            change_description="change buffer depth",
        )

        stored_parent = controller.repository.get_design(parent.design_id)
        self.assertEqual(stored_parent.source_revision, "abc123")
        self.assertEqual(first.parent_design_id, parent.design_id)
        self.assertEqual(second.parent_design_id, parent.design_id)
        self.assertEqual(len(controller.repository.list_designs()), 3)

    def test_artifacts_are_content_addressed_and_deduplicated(self) -> None:
        store = ArtifactStore(self.root / "artifacts")
        first = store.put_text("stdout", "same content")
        second = store.put_text("log", "same content")
        self.assertEqual(first.sha256, second.sha256)
        self.assertEqual(first.path, second.path)
        self.assertTrue(Path(first.path).is_file())

    def test_declared_output_is_archived_from_workspace(self) -> None:
        output = "{workspace}/outputs/{evaluation_id}/result.json"
        script = (
            "from pathlib import Path; import sys; "
            "path = Path(sys.argv[1]); path.parent.mkdir(parents=True); path.write_text('{}')"
        )
        evaluators = {
            "emit": {
                "phase": "verification",
                "command": [sys.executable, "-c", script, output],
                "outputs": [output],
            }
        }
        controller = ExplorationController(self.root / "workspace", self._write_config(evaluators))
        design = controller.create_design(
            source_revision="abc123", hypothesis="artifact", change_description="emit report"
        )
        report = asyncio.run(controller.run_profile(design.design_id, "test"))
        evaluation = report["evaluations"][0]
        self.assertEqual(evaluation["status"], EvaluationStatus.PASSED.value)
        self.assertIn("emit.result.json", {artifact["kind"] for artifact in evaluation["artifacts"]})
        output_path = Path(evaluation["command"][-1])
        self.assertTrue(output_path.is_file())
        self.assertEqual(output_path.parent.name, evaluation["evaluation_id"])

    def test_profile_runs_dependencies_and_promotes_on_pass(self) -> None:
        evaluators = {
            "contract": {
                "phase": "architecture_spec",
                "cost": 0,
                "command": [sys.executable, "-c", "print('contract pass')"],
            },
            "sim_a": {
                "phase": "verification",
                "cost": 1,
                "requires": ["contract"],
                "command": [sys.executable, "-c", "print('sim a pass')"],
            },
            "sim_b": {
                "phase": "verification",
                "cost": 1,
                "requires": ["contract"],
                "command": [sys.executable, "-c", "print('sim b pass')"],
            },
        }
        controller = ExplorationController(self.root / "workspace", self._write_config(evaluators))
        design = controller.create_design(
            source_revision="abc123", hypothesis="parallel", change_description="two simulations"
        )
        report = asyncio.run(controller.run_profile(design.design_id, "test"))

        self.assertEqual(report["decision"]["action"], DecisionAction.PROMOTE.value)
        statuses = {record["evaluator"]: record["status"] for record in report["evaluations"]}
        self.assertEqual(statuses, {"contract": "passed", "sim_a": "passed", "sim_b": "passed"})
        artifacts = report["evaluations"][0]["artifacts"]
        self.assertEqual({artifact["kind"] for artifact in artifacts}, {"contract.stdout", "contract.stderr"})

    def test_failed_cheap_gate_skips_expensive_descendants(self) -> None:
        marker = self.root / "must-not-run"
        evaluators = {
            "lint": {
                "phase": "verification",
                "cost": 0,
                "command": [sys.executable, "-c", "raise SystemExit(2)"],
            },
            "synth": {
                "phase": "physical",
                "cost": 4,
                "resource": "vivado",
                "requires": ["lint"],
                "command": [sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"],
            },
            "route": {
                "phase": "physical",
                "cost": 5,
                "resource": "vivado",
                "requires": ["synth"],
                "command": [sys.executable, "-c", "pass"],
            },
        }
        controller = ExplorationController(self.root / "workspace", self._write_config(evaluators))
        design = controller.create_design(
            source_revision="abc123", hypothesis="bad lint", change_description="should stop early"
        )
        report = asyncio.run(controller.run_profile(design.design_id, "test"))

        statuses = {record["evaluator"]: record["status"] for record in report["evaluations"]}
        self.assertEqual(statuses["lint"], EvaluationStatus.FAILED.value)
        self.assertEqual(statuses["synth"], EvaluationStatus.SKIPPED.value)
        self.assertEqual(statuses["route"], EvaluationStatus.SKIPPED.value)
        self.assertEqual(report["decision"]["action"], DecisionAction.REPAIR.value)
        self.assertFalse(marker.exists())

    def test_expensive_profile_requires_explicit_opt_in(self) -> None:
        evaluators = {
            "vivado": {
                "phase": "fpga_build",
                "explicit_only": True,
                "command": [sys.executable, "-c", "pass"],
            }
        }
        config = self._write_config(evaluators)
        with self.assertRaises(PermissionError):
            config.specs_for("test")
        self.assertEqual(set(config.specs_for("test", allow_expensive=True)), {"vivado"})

    def test_configuration_rejects_dependency_cycle(self) -> None:
        evaluators = {
            "first": {
                "phase": "verification",
                "requires": ["second"],
                "command": [sys.executable, "-c", "pass"],
            },
            "second": {
                "phase": "verification",
                "requires": ["first"],
                "command": [sys.executable, "-c", "pass"],
            },
        }
        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            self._write_config(evaluators)

    def test_timeout_terminates_evaluator(self) -> None:
        evaluators = {
            "slow": {
                "phase": "verification",
                "timeout_seconds": 0.05,
                "command": [sys.executable, "-c", "import time; time.sleep(60)"],
            }
        }
        controller = ExplorationController(self.root / "workspace", self._write_config(evaluators))
        design = controller.create_design(
            source_revision="abc123", hypothesis="timeout", change_description="exercise timeout"
        )
        report = asyncio.run(controller.run_profile(design.design_id, "test"))
        evaluation = report["evaluations"][0]
        self.assertEqual(evaluation["status"], EvaluationStatus.TIMEOUT.value)
        self.assertEqual(report["decision"]["action"], DecisionAction.REPAIR.value)

    def test_profile_rejects_source_changes_after_candidate_creation(self) -> None:
        source = self.repo / "design.sv"
        source.write_text("module design; endmodule\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo, check=True)
        subprocess.run(["git", "add", "design.sv"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.repo, check=True)
        evaluators = {
            "pass": {"phase": "verification", "command": [sys.executable, "-c", "pass"]}
        }
        controller = ExplorationController(self.root / "workspace", self._write_config(evaluators))
        design = controller.create_design(
            source_revision=current_revision(self.repo),
            hypothesis="immutable source",
            change_description="baseline",
            constraints={"source_state": capture_source_state(self.repo, allow_dirty=False)},
        )
        source.write_text("module design; wire changed; endmodule\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "fingerprint"):
            asyncio.run(controller.run_profile(design.design_id, "test"))

    def test_agent_decision_cannot_bypass_promotion_gate(self) -> None:
        with self.assertRaises(ValueError):
            AgentDecision.validate(
                {"action": "promote", "parent_design_id": "design-1", "evaluations": []},
                {"contract"},
            )
        decision = AgentDecision.validate(
            {
                "action": "repair",
                "parent_design_id": "design-1",
                "hypothesis": "timing path",
                "change_description": "pipeline multiplier",
                "evaluations": ["contract"],
            },
            {"contract"},
        )
        self.assertEqual(decision.action, DecisionAction.REPAIR)
        fork = AgentDecision.validate(
            {
                "action": "fork",
                "parent_design_id": "design-1",
                "hypothesis": "alternate pipeline",
                "change_description": "change pipeline depth",
                "evaluations": ["contract"],
            },
            {"contract"},
        )
        self.assertEqual(fork.action, DecisionAction.FORK)


if __name__ == "__main__":
    unittest.main()

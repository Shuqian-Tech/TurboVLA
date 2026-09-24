"""Async local command execution with resource limits and artifact capture."""

from __future__ import annotations

import asyncio
import os
import signal
import time
from pathlib import Path

from .artifacts import ArtifactStore
from .evaluators import EvaluatorSpec
from .models import Evaluation, EvaluationStatus, new_id, utc_now


class LocalExecutor:
    def __init__(
        self,
        repo_root: Path,
        workspace: Path,
        artifacts: ArtifactStore,
        resources: dict[str, int],
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.workspace = workspace.resolve()
        self.artifacts = artifacts
        self._resources = {
            name: asyncio.Semaphore(capacity)
            for name, capacity in resources.items()
            if capacity > 0
        }

    async def run(self, design_id: str, spec: EvaluatorSpec) -> Evaluation:
        semaphore = self._resources.get(spec.resource)
        if semaphore is None:
            return self._error(design_id, spec, f"resource {spec.resource!r} has no configured capacity")
        async with semaphore:
            return await self._run_locked(design_id, spec)

    async def _run_locked(self, design_id: str, spec: EvaluatorSpec) -> Evaluation:
        evaluation_id = new_id("evaluation")
        started_at = utc_now()
        started = time.monotonic()
        command = tuple(self._expand(value, evaluation_id) for value in spec.command)
        run_directory = self.workspace / "runs" / evaluation_id
        run_directory.mkdir(parents=True)
        stdout_path = run_directory / "stdout.log"
        stderr_path = run_directory / "stderr.log"
        environment = os.environ.copy()
        environment.update(spec.environment)
        try:
            with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=self.repo_root,
                    env=environment,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    start_new_session=True,
                )
                try:
                    await asyncio.wait_for(process.wait(), timeout=spec.timeout_seconds)
                    return_code = process.returncode
                    status = EvaluationStatus.PASSED if return_code == 0 else EvaluationStatus.FAILED
                    message = "command passed" if return_code == 0 else f"command exited with {return_code}"
                except asyncio.TimeoutError:
                    self._signal_process_group(process, signal.SIGTERM)
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        self._signal_process_group(process, signal.SIGKILL)
                        await process.wait()
                    return_code = process.returncode
                    status = EvaluationStatus.TIMEOUT
                    message = f"command exceeded {spec.timeout_seconds:g}s timeout"
        except (FileNotFoundError, OSError) as error:
            return self._error(design_id, spec, str(error), command, evaluation_id, started_at, started)

        artifacts = [
            self.artifacts.put_file(f"{spec.name}.stdout", stdout_path),
            self.artifacts.put_file(f"{spec.name}.stderr", stderr_path),
        ]
        missing_outputs = []
        for configured_path in spec.outputs:
            output_path = Path(self._expand(configured_path, evaluation_id))
            if not output_path.is_absolute():
                output_path = self.repo_root / output_path
            try:
                output_path.resolve().relative_to(self.workspace)
            except ValueError:
                missing_outputs.append(f"unsafe output outside workspace: {output_path}")
                continue
            if output_path.is_file():
                artifacts.append(self.artifacts.put_file(f"{spec.name}.{output_path.name}", output_path))
            else:
                missing_outputs.append(str(output_path))
        if status == EvaluationStatus.PASSED and missing_outputs:
            status = EvaluationStatus.ERROR
            message = f"command did not produce required outputs: {', '.join(missing_outputs)}"
        return Evaluation(
            evaluation_id=evaluation_id,
            design_id=design_id,
            evaluator=spec.name,
            phase=spec.phase,
            status=status,
            command=command,
            started_at=started_at,
            finished_at=utc_now(),
            duration_seconds=time.monotonic() - started,
            return_code=return_code,
            artifacts=tuple(artifacts),
            message=message,
        )

    @staticmethod
    def _signal_process_group(process: asyncio.subprocess.Process, requested_signal: signal.Signals) -> None:
        try:
            os.killpg(process.pid, requested_signal)
        except ProcessLookupError:
            return

    @staticmethod
    def _error(
        design_id: str,
        spec: EvaluatorSpec,
        message: str,
        command: tuple[str, ...] | None = None,
        evaluation_id: str | None = None,
        started_at: str | None = None,
        started: float | None = None,
    ) -> Evaluation:
        return Evaluation(
            evaluation_id=evaluation_id or new_id("evaluation"),
            design_id=design_id,
            evaluator=spec.name,
            phase=spec.phase,
            status=EvaluationStatus.ERROR,
            command=command or spec.command,
            started_at=started_at or utc_now(),
            finished_at=utc_now(),
            duration_seconds=0.0 if started is None else time.monotonic() - started,
            return_code=None,
            message=message,
        )

    def _expand(self, value: str, evaluation_id: str) -> str:
        return value.replace("{workspace}", str(self.workspace)).replace(
            "{evaluation_id}", evaluation_id
        )

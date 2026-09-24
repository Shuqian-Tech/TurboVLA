"""SQLite repository for design lineage, evaluations, and events."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import ArtifactRef, DesignState, Evaluation, EvaluationStatus, Event


class SqliteRepository:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS designs (
                    design_id TEXT PRIMARY KEY,
                    parent_design_id TEXT REFERENCES designs(design_id),
                    source_revision TEXT NOT NULL,
                    target_fpga TEXT NOT NULL,
                    hypothesis TEXT NOT NULL,
                    change_description TEXT NOT NULL,
                    constraints_json TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evaluations (
                    evaluation_id TEXT PRIMARY KEY,
                    design_id TEXT NOT NULL REFERENCES designs(design_id),
                    evaluator TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    status TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    finished_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    design_id TEXT NOT NULL REFERENCES designs(design_id),
                    evaluation_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_evaluations_design ON evaluations(design_id, finished_at);
                CREATE INDEX IF NOT EXISTS idx_events_design ON events(design_id, created_at);
                """
            )

    def add_design(self, design: DesignState, event: Event | None = None) -> None:
        if design.target_fpga != "kr260-k26":
            raise ValueError("only KR260/K26 candidates are supported")
        if design.parent_design_id is not None:
            self.get_design(design.parent_design_id)
        if event is not None and event.design_id != design.design_id:
            raise ValueError("design event must reference the inserted design")
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO designs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    design.design_id,
                    design.parent_design_id,
                    design.source_revision,
                    design.target_fpga,
                    design.hypothesis,
                    design.change_description,
                    json.dumps(design.constraints, sort_keys=True),
                    design.created_by,
                    design.created_at,
                ),
            )
            if event is not None:
                self._insert_event(connection, event)

    def get_design(self, design_id: str) -> DesignState:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM designs WHERE design_id = ?", (design_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown design: {design_id}")
        return DesignState(
            design_id=row["design_id"],
            parent_design_id=row["parent_design_id"],
            source_revision=row["source_revision"],
            target_fpga=row["target_fpga"],
            hypothesis=row["hypothesis"],
            change_description=row["change_description"],
            constraints=json.loads(row["constraints_json"]),
            created_by=row["created_by"],
            created_at=row["created_at"],
        )

    def list_designs(self) -> list[DesignState]:
        with self._connect() as connection:
            ids = [row[0] for row in connection.execute("SELECT design_id FROM designs ORDER BY created_at")]
        return [self.get_design(design_id) for design_id in ids]

    def add_evaluation(self, evaluation: Evaluation, event: Event | None = None) -> None:
        self.get_design(evaluation.design_id)
        if event is not None and (
            event.design_id != evaluation.design_id
            or event.evaluation_id != evaluation.evaluation_id
        ):
            raise ValueError("evaluation event must reference the inserted evaluation")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO evaluations VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    evaluation.evaluation_id,
                    evaluation.design_id,
                    evaluation.evaluator,
                    evaluation.phase,
                    evaluation.status.value,
                    json.dumps(evaluation.to_dict(), sort_keys=True),
                    evaluation.finished_at,
                ),
            )
            if event is not None:
                self._insert_event(connection, event)

    def evaluations_for(self, design_id: str) -> list[Evaluation]:
        self.get_design(design_id)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT record_json FROM evaluations WHERE design_id = ? ORDER BY finished_at", (design_id,)
            ).fetchall()
        return [self._evaluation_from_dict(json.loads(row[0])) for row in rows]

    def latest_statuses(self, design_id: str) -> dict[str, EvaluationStatus]:
        latest: dict[str, EvaluationStatus] = {}
        for evaluation in self.evaluations_for(design_id):
            latest[evaluation.evaluator] = evaluation.status
        return latest

    def add_event(self, event: Event) -> None:
        self.get_design(event.design_id)
        with self._connect() as connection:
            self._insert_event(connection, event)

    @staticmethod
    def _insert_event(connection: sqlite3.Connection, event: Event) -> None:
        connection.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                event.design_id,
                event.evaluation_id,
                event.event_type,
                json.dumps(event.payload, sort_keys=True),
                event.created_at,
            ),
        )

    def events_for(self, design_id: str) -> list[Event]:
        self.get_design(design_id)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE design_id = ? ORDER BY created_at", (design_id,)
            ).fetchall()
        return [
            Event(
                event_id=row["event_id"],
                event_type=row["event_type"],
                design_id=row["design_id"],
                evaluation_id=row["evaluation_id"],
                payload=json.loads(row["payload_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    @staticmethod
    def _evaluation_from_dict(record: dict) -> Evaluation:
        artifacts = tuple(ArtifactRef(**artifact) for artifact in record["artifacts"])
        return Evaluation(
            evaluation_id=record["evaluation_id"],
            design_id=record["design_id"],
            evaluator=record["evaluator"],
            phase=record["phase"],
            status=EvaluationStatus(record["status"]),
            command=tuple(record["command"]),
            started_at=record["started_at"],
            finished_at=record["finished_at"],
            duration_seconds=record["duration_seconds"],
            return_code=record["return_code"],
            artifacts=artifacts,
            metrics=record["metrics"],
            message=record["message"],
        )

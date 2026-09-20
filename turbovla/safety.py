"""Safety boundary for software replay and the future KR260 robot driver."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SafetyDecision:
    accepted: bool
    reason: str
    action: np.ndarray


@dataclass
class SafetyPolicy:
    action_low: float = -1.0
    action_high: float = 1.0
    timeout_seconds: float = 0.25
    emergency_stop: bool = False
    communication_connected: bool = True
    last_frame_time: float | None = None

    def apply(self, action: np.ndarray, now: float | None = None) -> SafetyDecision:
        timestamp = time.monotonic() if now is None else float(now)
        candidate = np.asarray(action, dtype=np.float32)
        if candidate.shape != (1, 12, 7):
            return SafetyDecision(False, "invalid_shape", np.zeros((1, 12, 7), dtype=np.float32))
        if not np.isfinite(candidate).all():
            return SafetyDecision(False, "non_finite_action", np.zeros_like(candidate))
        if self.emergency_stop:
            return SafetyDecision(False, "emergency_stop", np.zeros_like(candidate))
        if not self.communication_connected:
            return SafetyDecision(False, "communication_disconnected", np.zeros_like(candidate))
        if self.last_frame_time is not None and timestamp - self.last_frame_time > self.timeout_seconds:
            return SafetyDecision(False, "frame_timeout", np.zeros_like(candidate))
        self.last_frame_time = timestamp
        return SafetyDecision(True, "accepted", np.clip(candidate, self.action_low, self.action_high))


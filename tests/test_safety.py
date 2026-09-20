from __future__ import annotations

import unittest

import numpy as np

from turbovla.safety import SafetyPolicy


class SafetyTest(unittest.TestCase):
    def test_clamps_accepted_action(self) -> None:
        policy = SafetyPolicy()
        decision = policy.apply(np.full((1, 12, 7), 2.0, dtype=np.float32), now=0.0)
        self.assertTrue(decision.accepted)
        self.assertEqual(float(decision.action.max()), 1.0)

    def test_faults_reject_action(self) -> None:
        action = np.zeros((1, 12, 7), dtype=np.float32)
        policy = SafetyPolicy()
        action[0, 0, 0] = np.nan
        self.assertEqual(policy.apply(action, now=0.0).reason, "non_finite_action")
        policy.emergency_stop = True
        self.assertEqual(policy.apply(np.zeros_like(action), now=0.0).reason, "emergency_stop")
        policy.emergency_stop = False
        policy.last_frame_time = 0.0
        self.assertEqual(policy.apply(np.zeros_like(action), now=1.0).reason, "frame_timeout")


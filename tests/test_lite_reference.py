from __future__ import annotations

import unittest

import numpy as np

from turbovla.lite_reference import ReferenceInputError, TurboVLALiteReference, deterministic_sample


class LiteReferenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = TurboVLALiteReference()
        self.sample = deterministic_sample(self.model.contract)

    def test_fixed_shapes_and_repeatability(self) -> None:
        first = self.model.run(*self.sample)
        second = self.model.run(*self.sample)
        self.assertEqual(first["visual_tokens"].shape, (1, 32, 128))
        self.assertEqual(first["action"].shape, (1, 12, 7))
        for name in first:
            np.testing.assert_array_equal(first[name], second[name], err_msg=name)

    def test_int8_trace_matches_fp32_within_reference_budget(self) -> None:
        report = self.model.compare(*self.sample)
        self.assertLess(report["action"]["max_abs_error"], 0.05)
        self.assertLess(report["action"]["mean_abs_error"], 0.02)

    def test_invalid_instruction_id_uses_contract_error(self) -> None:
        image, state, instruction_id = self.sample
        invalid = np.asarray([65535], dtype=np.uint16)
        with self.assertRaises(ReferenceInputError) as context:
            self.model.run(image, state, invalid)
        self.assertEqual(context.exception.code, self.model.contract["errors"]["invalid_instruction_id"])

    def test_invalid_image_shape_uses_buffer_error(self) -> None:
        _, state, instruction_id = self.sample
        invalid_image = np.zeros((1, 1, 3, 64, 64), dtype=np.uint8)
        with self.assertRaises(ReferenceInputError) as context:
            self.model.run(invalid_image, state, instruction_id)
        self.assertEqual(context.exception.code, self.model.contract["errors"]["invalid_buffer"])


if __name__ == "__main__":
    unittest.main()


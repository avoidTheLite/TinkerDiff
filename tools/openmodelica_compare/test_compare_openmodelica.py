#!/usr/bin/env python3
"""Unit tests for openmodelica compare (offline structure checks)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import compare_openmodelica as cmp


class CompareTests(unittest.TestCase):
    def test_repo_baseline_valid(self) -> None:
        data = cmp.load_json(cmp.DEFAULT_BASELINE)
        errs = cmp.validate_baseline(data)
        self.assertEqual(errs, [], errs)

    def test_repo_forms_valid(self) -> None:
        data = cmp.load_json(cmp.DEFAULT_FORMS)
        errs = cmp.validate_forms(data)
        self.assertEqual(errs, [], errs)

    def test_main_offline_pass(self) -> None:
        self.assertEqual(cmp.main([]), 0)

    def test_duplicate_role_fails(self) -> None:
        data = cmp.load_json(cmp.DEFAULT_BASELINE)
        data["components"].append(dict(data["components"][0]))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(cmp.main(["--baseline", str(path)]), 1)

    def test_require_role(self) -> None:
        self.assertEqual(cmp.main(["--require-role", "capacitance"]), 0)
        self.assertEqual(cmp.main(["--require-role", "not_a_real_role"]), 1)


if __name__ == "__main__":
    unittest.main()

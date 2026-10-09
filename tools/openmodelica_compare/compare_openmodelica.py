#!/usr/bin/env python3
"""Compare TinkerDiff OpenModelica analogy baseline to live MSL helpOM pages.

Validates:
  - baseline JSON structure
  - every component has modelica_path, equations, and a validation class
  - optional --fetch: download doc pages and check modelica_info_match appears
  - optional --require-role: fail if a named role is missing (for new components)

Exit codes: 0 ok, 1 validation failure, 2 usage / I/O error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE = (
    ROOT / "engineering-components" / "analogies" / "openmodelica-baseline.json"
)
DEFAULT_FORMS = ROOT / "engineering-components" / "analogies" / "resistance-forms.json"

ALLOWED_VALIDATION = {
    "pass_ideal",
    "pass_ideal_gamma0",
    "pass_with_convention",
    "pass_family",
    "intentional_simplification",
    "related_not_identical",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", "".join(self._chunks)).strip()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def normalize_needle(s: str) -> str:
    s = s.lower()
    s = s.replace("Δ", "d").replace("·", "*").replace("×", "*")
    s = re.sub(r"\s+", "", s)
    s = s.replace("\\,", "").replace("\\,", "")
    return s


def validate_baseline(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("schema_version", "msl_version", "doc_base", "components"):
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    comps = data.get("components")
    if not isinstance(comps, list) or not comps:
        errors.append("components must be a non-empty list")
        return errors

    roles: set[str] = set()
    for i, c in enumerate(comps):
        prefix = f"components[{i}]"
        if not isinstance(c, dict):
            errors.append(f"{prefix}: must be object")
            continue
        for req in (
            "tinkerdiff_role",
            "element_type",
            "modelica_path",
            "doc_url",
            "tinkerdiff_equation",
            "modelica_equation",
            "modelica_info_match",
            "equation_delta",
            "validation",
        ):
            if req not in c or c[req] in ("", None):
                errors.append(f"{prefix}: missing {req}")
        role = c.get("tinkerdiff_role")
        if isinstance(role, str):
            if role in roles:
                errors.append(f"duplicate tinkerdiff_role: {role}")
            roles.add(role)
        if c.get("validation") not in ALLOWED_VALIDATION:
            errors.append(
                f"{prefix}: validation must be one of {sorted(ALLOWED_VALIDATION)}"
            )
        path = c.get("modelica_path", "")
        url = c.get("doc_url", "")
        if path and url and path not in url:
            errors.append(f"{prefix}: doc_url does not contain modelica_path")
        et = c.get("element_type")
        if et not in ("capacitance", "inductance", "resistance", "transformer"):
            errors.append(f"{prefix}: invalid element_type {et!r}")
    return errors


def validate_forms(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    forms = data.get("forms")
    if not isinstance(forms, list) or not forms:
        return ["resistance-forms: forms must be a non-empty list"]
    ids: set[str] = set()
    for i, f in enumerate(forms):
        fid = f.get("id")
        if not fid:
            errors.append(f"forms[{i}]: missing id")
            continue
        if fid in ids:
            errors.append(f"duplicate form id: {fid}")
        ids.add(fid)
        for req in ("equation", "selection_hints", "standard_labels"):
            if req not in f:
                errors.append(f"forms[{i}] ({fid}): missing {req}")
    if data.get("default_form") not in ids:
        errors.append("default_form must reference a defined form id")
    return errors


def fetch_text(url: str, timeout: float = 30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "TinkerDiff-OM-Compare/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    parser = _TextExtractor()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return parser.text()


def check_fetch(components: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for c in components:
        role = c["tinkerdiff_role"]
        url = c["doc_url"]
        needle = c["modelica_info_match"]
        try:
            text = fetch_text(url)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            errors.append(f"{role}: fetch failed for {url}: {exc}")
            continue
        if normalize_needle(needle) not in normalize_needle(text):
            # allow loose token presence for short math snippets
            tokens = [t for t in re.split(r"[^a-z0-9]+", needle.lower()) if len(t) > 1]
            missing = [t for t in tokens if t not in text.lower()]
            if missing:
                errors.append(
                    f"{role}: doc drift — info match {needle!r} not found at {url} "
                    f"(missing tokens: {missing})"
                )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
        help="Path to openmodelica-baseline.json",
    )
    parser.add_argument(
        "--forms",
        type=Path,
        default=DEFAULT_FORMS,
        help="Path to resistance-forms.json",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch live OpenModelica helpOM pages and check info strings",
    )
    parser.add_argument(
        "--require-role",
        action="append",
        default=[],
        help="Fail if this tinkerdiff_role is absent (repeatable)",
    )
    args = parser.parse_args(argv)

    try:
        baseline = load_json(args.baseline)
        forms = load_json(args.forms)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    errors = validate_baseline(baseline) + validate_forms(forms)
    roles = {c.get("tinkerdiff_role") for c in baseline.get("components", [])}
    for role in args.require_role:
        if role not in roles:
            errors.append(f"required role missing from baseline: {role}")

    if args.fetch and not errors:
        print("Fetching OpenModelica documentation pages…")
        errors.extend(check_fetch(baseline["components"]))

    if errors:
        print("OpenModelica compare: FAIL")
        for e in errors:
            print(f"  - {e}")
        return 1

    n = len(baseline["components"])
    print(f"OpenModelica compare: PASS ({n} baseline components, forms ok)")
    if args.fetch:
        print("  live doc info strings matched")
    return 0


if __name__ == "__main__":
    sys.exit(main())

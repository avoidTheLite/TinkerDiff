# OpenModelica compare check

Keeps TinkerDiff’s named equivalent models honest against OpenModelica / MSL **v4.0.0** documentation.

## Artifacts

| File | Role |
|------|------|
| [`../../engineering-components/analogies/openmodelica-baseline.json`](../../engineering-components/analogies/openmodelica-baseline.json) | Closest MSL path, both equations, and intentional deltas |
| [`../../engineering-components/analogies/resistance-forms.json`](../../engineering-components/analogies/resistance-forms.json) | Resistance form catalog |

## Usage

```bash
# Structure + catalog validation (offline, default CI)
python3 tools/openmodelica_compare/compare_openmodelica.py

# Also fetch live helpOM pages and confirm info strings still match
python3 tools/openmodelica_compare/compare_openmodelica.py --fetch

# Fail if a role is missing when onboarding a new named component
python3 tools/openmodelica_compare/compare_openmodelica.py --require-role capacitance
```

```bash
python3 -m unittest tools.openmodelica_compare.test_compare_openmodelica
# or from this directory:
python3 test_compare_openmodelica.py
```

## When to update the baseline

- Changing a constitutive equation for R / C / I / TF
- Adding a new named equivalent model or Resistance form
- Bumping the referenced MSL version

`equation_delta` must record intentional simplifications (for example pressurized chamber vs `ClosedVolume`) so the check does not treat them as accidental drift.

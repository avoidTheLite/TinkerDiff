# Equivalent-model analogies

Physical names in TinkerDiff are **roles** (what a block does), not full product models. This directory holds the closest OpenModelica / MSL baselines and the Resistance form catalog so equation differences stay explicit.

| File | Purpose |
|------|---------|
| [openmodelica-baseline.json](openmodelica-baseline.json) | Named component ↔ MSL path, both equations, intentional deltas |
| [resistance-forms.json](resistance-forms.json) | Linear / orifice / check / deadzone / saturation / power_law laws and selection hints |

Run the compare check from the repo root:

```bash
python3 tools/openmodelica_compare/compare_openmodelica.py
python3 tools/openmodelica_compare/compare_openmodelica.py --fetch
```

See [01 Foundations §5](../01-foundations.md) for the pressurized-chamber example, Resistance forms, and port/sign conventions.

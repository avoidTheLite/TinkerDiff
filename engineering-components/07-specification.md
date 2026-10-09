# 07. Specification: Schema, Hydration, and Conformance

This document explains how the formal artifacts fit together. The JSON Schema is the source of truth for the object model; the other documents explain what its fields mean and how engines must use them.

## 1. Authority and Precedence

| Artifact | Role |
|----------|------|
| [`schema/tinkerdiff.schema.json`](schema/tinkerdiff.schema.json) | **Normative.** Defines every field, type, and structural constraint of a system model and of an engine's evaluation result. |
| `01`–`06` | Explain the meaning of the fields and the mathematics engines must implement. |
| [`conformance/vectors.json`](conformance/vectors.json) | Executable examples of the mathematics, with expected outputs. |
| [`schema/examples/`](schema/examples/) | Schema-valid models. |

If prose and the schema disagree, the schema wins. If prose and a conformance vector disagree on a number, the vector wins and the prose is a defect.

## 2. Schema Map

A model (the schema root) is a **System**:

```
System
 ├─ impact_unit            unit all consequences are expressed in
 ├─ evaluation             horizon, sampling interval, recalibration policy, risk measures
 ├─ assemblies[]
 │    ├─ nodes[]
 │    │    ├─ Subassembly  elements[], failure_modes[], propagation, escalation, ...
 │    │    └─ Vortex       io_contract, uncertainty (mandatory), consequence
 │    ├─ connections[]     Fittings between member nodes
 │    └─ structure         success logic over member nodes (optional; series if absent)
 ├─ connections[]          Fittings between nodes in different Assemblies
 └─ top_event              success logic (Structure) and its consequence
```

| Schema definition (`$defs/…`) | Explained in |
|--------------------------------|--------------|
| `Element` | [01 Foundations](01-foundations.md) |
| `Distribution`, `ProbabilityOrDistribution`, `ImpactUnit`, `ImpactModel` | [02 Risk Model](02-risk-model.md) |
| `FailureMode`, `HazardDriver` | [03 Failure Modes](03-failure-modes.md) |
| `Vortex`, `Escalation`, `Port` | [04 Vortex Components](04-vortex-black-box-components.md) |
| `Propagation`, `ProbabilityFlow`, `Evaluation` | [05 Execution Model](05-execution-model.md) |
| `RecalibrationPolicy` | [06 Drift Control](06-drift-control-and-recalibration.md) |
| `Structure`, `TopEvent` | [02 Risk Model](02-risk-model.md) §5 |
| `Assembly`, `Fitting`, `Endpoint`, `Subassembly` | [01 Foundations](01-foundations.md) §4 |
| `EvaluationResult` | §6 below |

### 2.1 Key Design Rules Encoded in the Schema

- **A Vortex cannot exist without an uncertainty distribution.** `uncertainty.reliability` and `consequence` are required.
- **A failure mode needs a cause model.** At least one of `fragility` (state-driven) and `baseline_hazard` (time-driven) is required.
- **Uncertain values are distributions.** Anywhere the model accepts a probability it may accept a distribution instead, which is how uncertainty is carried into the risk output.
- **Drift control is one object.** Recalibration scheduling, the drift model, and the accuracy requirement live together in `RecalibrationPolicy`, at the system level with an optional per-node override.
- **Time is in seconds.** Duration fields end in `_sec` (or `_ms` where stated).

## 3. Hydration: Structure to Executable Model

A system is described in two layers ([01](01-foundations.md) §7): a structural blueprint, typically exported from an architecture document, and parameter data that supplies the physics and uncertainty. **Hydration** joins them into a schema-valid model.

```
[ Architecture export: UML XMI or JSON manifest ]
                   |
                   v
        [ Structural parser ]  -----> topology: components, interfaces, connectors
                   |
                   v
       [ Parameter hydrator ]  <----- parameter data: Elements, failure modes, distributions
                   |
                   v
      [ Schema validation (§4) ]
                   |
                   v
        [ System model (JSON) ]  -----> engine
```

Rules:

1. Each architecture grouping (a UML package or subsystem) becomes an **Assembly**; components outside any grouping go into a default Assembly.
2. Each architecture component with parameter data becomes a **Subassembly**. Its architecture identifier is kept in `source_reference.id`, and its provided and required interfaces in `interfaces`.
3. A component with **no** parameter data hydrates to a **Vortex** with `knowledge_level: unknown` and a conservative prior, so missing information increases risk rather than being ignored. The I/O contract is taken from the component's interfaces.
4. Connectors become **Fittings** between the corresponding interfaces.
5. The hydrator never invents parameters for a Subassembly. A Subassembly with missing parameters is a validation error (§4).

## 4. Validation

Validation has two stages. The first is JSON Schema validation, which an engine must perform before accepting a model. The second covers constraints that JSON Schema cannot express, which an engine must also enforce:

| Check | Rule |
|-------|------|
| Unique identifiers | `assembly_id` is unique across the model; `node_id` is unique across all Assemblies; `element_id` is unique within a Subassembly; `mode_id` is unique across the model |
| Reference integrity | `Endpoint.node_id`, `Structure` leaves, `Propagation.targets`, `Escalation.vortex_ref`, and `refinement.subassembly_ref` must name existing nodes (the last may name a node outside the model); an `assembly` leaf must name an existing Assembly |
| Assembly scope | An Assembly's `structure` references only its own member nodes; an Assembly's `connections` join only its own members; `System.connections` join nodes in different Assemblies; the top-event structure may reference nodes or Assemblies |
| Element references | `FailureMode.element_ref` must name an Element in the same Subassembly; `Endpoint.element_id` must name an Element in the referenced node |
| Propagation shape | `weights` has `len(targets)` rows and `len(inputs)` columns; each `inputs` entry is a `mode_id` of the same node |
| Escalation target | `vortex_ref` must name a Vortex of class `inference` |
| Structure | `k_of_n` has $1 \le k \le N$; `failover` has exactly two inputs; a node appears in the structure at most once unless a shared-cause model is declared |
| Distributions | Parameters must give a valid distribution (for example `Uniform.min < Uniform.max`); distributions used as probabilities must be supported on $[0,1]$ |
| Acyclic propagation | The propagation graph must be acyclic. Cyclic feedback is not supported in schema version 0.1.0 and must be rejected |
| Single unit | All consequences are in `impact_unit`; the schema cannot check this, so the modeler is responsible |

Validation errors must identify the offending path and the violated rule.

## 5. Engine Obligations

An engine in any language is conforming when it:

1. Accepts every model that passes §4 and rejects every model that fails it, with a precise error.
2. Reproduces every value in [`conformance/vectors.json`](conformance/vectors.json) within the stated tolerance.
3. Honors the evaluation lifecycle and consistency rules in [05](05-execution-model.md) §6 and [06](06-drift-control-and-recalibration.md) §3: bounded incremental cost, consistent snapshots, non-blocking atomic publication, and no lost updates when merging a recalibration.
4. Reports results that validate against `#/$defs/EvaluationResult`.
5. Is reproducible: the same model, input log, and `random_seed` yield the same result, except where an inference-class Vortex is invoked (those invocations are recorded).

Engines choose their own concurrency mechanisms, numerical libraries, and sampling strategies. The specification fixes behavior and tolerances, not implementation.

## 6. Evaluation Result

`#/$defs/EvaluationResult` is the engine's output. It contains:

| Field | Content |
|-------|---------|
| `flow_state`, `turbulence_causes` | Laminar or Turbulent, with the conditions from [04](04-vortex-black-box-components.md) §6 that apply |
| `risk` | `expected_value`, `quantiles`, optional tail measure, and the epistemic share of variance ([02](02-risk-model.md) §1.2) |
| `assemblies`, `nodes` | Per-Assembly and per-node availability, attribution entropy, and state |
| `drift` | Accumulated variance, accuracy confidence, last recalibration time, and missed ticks ([06](06-drift-control-and-recalibration.md) §4) |

## 7. Conformance Vectors

Each vector in `conformance/vectors.json` has an `id`, the `spec` section defining the computation, an `input`, an `expected` output, and a `tolerance` (absolute or relative). Vectors cover Element updates, Beta statistics, fragility and competing-risk calculations, combination rules, matrix propagation (both modes), adaptation validation, drift accounting, the probability-flow solutions (the closed-form Gaussian and the Laplace-domain Green's function, which must agree under inverse transform), and two end-to-end evaluations of `schema/examples/cloud-service.json`.

### 5.1 OpenModelica analogy compare

Named equivalent models (resistor, capacitor, pressurized chamber, orifice, and so on) are recorded in [`analogies/openmodelica-baseline.json`](analogies/openmodelica-baseline.json) with the TinkerDiff equation, the closest MSL equation, and an `equation_delta` for intentional simplifications. Resistance form ids live in [`analogies/resistance-forms.json`](analogies/resistance-forms.json).

Engines and contributors must keep those files in sync when constitutive laws or new named roles change. The offline check is:

```bash
python3 tools/openmodelica_compare/compare_openmodelica.py
```

Use `--fetch` to re-validate live OpenModelica helpOM info strings, and `--require-role <role>` when onboarding a new named component so the baseline cannot omit it.

An engine's test suite should load the vectors, run each computation, and compare. The vectors are designed to be loaded by a small harness in any language; none requires a language-specific feature.

## 8. Versioning

The schema uses semantic versioning, declared by `schema_version` in each model. Backward-compatible additions (new optional fields, new enum values) increment the minor version; changes that can invalidate an existing model increment the major version. An engine must reject a model whose major version it does not support. The conformance vectors carry their own `vectors_version`.

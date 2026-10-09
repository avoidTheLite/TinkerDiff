# Engineering Components Specification

This directory specifies the TinkerDiff model independently of any implementation language. Engines in any language implement the same object model (the JSON Schema) and must reproduce the values in the conformance vectors.

## Reading Order

| # | Document | Covers |
|---|----------|--------|
| - | [notation.md](notation.md) | Symbols, units, and conventions used throughout |
| 1 | [01-foundations.md](01-foundations.md) | Effort/flow, the four Element types, composition into Subassemblies |
| 2 | [02-risk-model.md](02-risk-model.md) | Risk definition, uncertainty, hazard rates, combination rules, risk output |
| 3 | [03-failure-modes.md](03-failure-modes.md) | Failure-mode channels, competing risk, root-cause attribution |
| 4 | [04-vortex-black-box-components.md](04-vortex-black-box-components.md) | Black-box components, mandatory uncertainty, the non-determinism boundary |
| 5 | [05-execution-model.md](05-execution-model.md) | Layers, operators, cost tiers, interval-driven evaluation, Laplace operator |
| 6 | [06-drift-control-and-recalibration.md](06-drift-control-and-recalibration.md) | Scheduled re-anchoring, drift accounting, circuit breaker |
| 7 | [07-specification.md](07-specification.md) | Schema map, hydration pipeline, validation rules, conformance |

## Supporting Material

- `schema/tinkerdiff.schema.json`: normative object model.
- `schema/examples/`: schema-valid example models.
- `conformance/vectors.json`: input/expected-output pairs every engine must reproduce.
- `analogies/`: OpenModelica baselines and Resistance form catalog (equation deltas for equivalent models).
- `examples/cloud-service-uptime.md`: SRE worked example.
- `examples/learning-simulator.md`: behavioral reinforcement worked example.
- `../tools/openmodelica_compare/`: compare check for named-component drift against MSL helpOM.

## Conventions for This Specification

- Normative statements use "must", "should", and "may". The schema and the conformance vectors take precedence over prose if they disagree.
- Documents state the assumptions under which each formula holds. A formula used outside its stated assumptions is an approximation, and engines should account for that through the drift model in [06](06-drift-control-and-recalibration.md).
- Documents describe required behavior (for example "readers never observe a partially updated state"), not language mechanisms.

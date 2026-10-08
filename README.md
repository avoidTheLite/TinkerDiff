# TinkerDiff

TinkerDiff is a framework for modeling systems from atomic mathematical building blocks. One set of effort/flow equations covers physical infrastructure, software systems, and probabilistic risk. The primary application is site reliability engineering (SRE): computing the risk of a modeled system from the likelihood of failure, the impact of failure, and an object model that handles components whose internals are unknown, where less knowledge increases risk.

The specification is language-agnostic. Reference engines exist in Go and Python and are expected to conform to the schema and conformance vectors in `engineering-components/`.

## Vocabulary

These terms are canonical across all documents and the schema.

### Structural units

| Term | Definition |
|------|------------|
| **Element** | The atomic unit: a single physical parameter, differential equation, or discrete transformer. Four types: Capacitance, Inductance, Resistance, Transformer. |
| **Subassembly** | A group of interconnected Elements that models one real component (a compute node, a database tier, a sensor array, a microservice pipeline). Hosts the component's failure modes and downstream impact weights. |
| **Assembly** | A collection of Subassemblies and Vortices, with the Fittings between them and, optionally, the success logic that defines the Assembly's own availability (for example "2 of 3 zones" or "primary with failover"). Without success logic, an Assembly is available only if every member is. |
| **Fitting** | A typed adapter between interfaces: it maps one Element's or Subassembly's output to another's input, converting units, domains, or data shape. |
| **Vortex** | A black-box component whose internals are not modeled, or whose behavior is non-deterministic (for example an inference agent). Specified by its I/O contract and a mandatory uncertainty distribution. A Vortex may stand in for a whole system or Subassembly; if its internals become known it can be replaced by a Subassembly of Elements. |
| **System** | The whole model: one or more Assemblies plus the top event, impact unit, and evaluation policy (horizon, recalibration schedule, risk measures). |
| **Hub** | The planned registry and package manager for versioned, shareable Elements and Subassemblies. Not yet specified. |

### Evaluated states

| Term | Definition |
|------|------------|
| **Laminar** | The evaluation is deterministic and inside validated bounds: no Vortex is outside its declared limits, no escalation boundary is crossed, and the approximation-accuracy confidence is at or above its minimum. |
| **Turbulent** | At least one of those conditions fails. Results remain usable but carry widened uncertainty and are flagged. See [04 Vortex Components](engineering-components/04-vortex-black-box-components.md) for the exact conditions. |

## Risk Model in Brief

For each scenario $S_i$, risk combines a likelihood $p_i$ and an impact $x_i$. Both are treated as random variables because their parameters are uncertain. The result is a distribution of risk with an expected value, reported in a unit chosen by the modeling team (dollars by default; any quantifiable outcome is supported). Black-box components contribute wide distributions, so missing knowledge raises tail risk by construction.

## Repository Layout

```
README.md                          this file: overview and vocabulary
engineering-components/            language-agnostic specification
  README.md                        reading order and document map
  notation.md                      symbols and conventions
  01-foundations.md                effort/flow, Elements, composition
  02-risk-model.md                 likelihood, impact, uncertainty, risk output
  03-failure-modes.md              FMEA channels and competing risk
  04-vortex-black-box-components.md  Vortex components and the non-determinism boundary
  05-execution-model.md            operators, cost tiers, interval evaluation
  06-drift-control-and-recalibration.md  scheduled re-anchoring and accuracy accounting
  07-specification.md              how the schema, hydration, and conformance fit together
  schema/                          JSON Schema (normative) and examples
  conformance/                     language-neutral test vectors
  examples/                        worked examples
engine/                            reference engines (Go, Python); in progress
```

The JSON Schema in `engineering-components/schema/` is the source of truth for the object model. The Markdown documents explain it.

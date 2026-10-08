# 04. Vortex Components

A **Vortex** is a component whose internals are not modeled, or whose behavior is non-deterministic. It is the framework's representation of everything the Elements cannot describe: a third-party service, a vendor appliance, a legacy system, or an inference agent. Symbols are in [notation.md](notation.md).

The name comes from fluid dynamics, where a vortex is a localized, non-linear structure in an otherwise predictable flow field. Deterministic formulas stop being reliable at that point, and the model must rely on a declared contract and a probability distribution instead.

## 1. Why a Vortex Is a Higher-Level Component

A black box is not an atom. It stands in for a whole system or Subassembly. If its internals were known, it would decompose into Elements and be modeled as a Subassembly. A Vortex therefore:

- lives at the same level as a Subassembly in a system,
- is specified by an **I/O contract** and a **mandatory uncertainty distribution**,
- may carry an optional **refinement** reference to the Subassembly that will replace it once its internals are modeled. Replacement is a model change; it does not alter anything that depends on the Vortex's I/O contract.

## 2. Classes

| Class | Meaning | Example |
|-------|---------|---------|
| `opaque_system` | Deterministic in principle, but unobserved or unmodeled | External CDN, managed SaaS dependency |
| `inference` | Output is produced by an inference process and cannot be pre-computed | LLM agent, learned policy, diagnostic classifier |

The classes differ in evaluation state (§6). An inference Vortex introduces non-determinism into whatever it influences.

## 3. Required Specification

### 3.1 I/O Contract

The contract lists the Vortex's input and output ports. Each port has a name, a type or unit, and optionally a valid range. The contract defines what "failure" means for the Vortex: not meeting its output obligations given valid inputs. Optionally the contract records advertised service levels (for example a published availability), but these are claims, not evidence.

### 3.2 Mandatory Uncertainty

A Vortex must declare a distribution for its **reliability**: the probability that it meets its contract over the horizon. The default family is Beta:

\[
A_{\text{vortex}} \sim \text{Beta}(\alpha, \beta), \qquad
E[A] = \frac{\alpha}{\alpha+\beta}, \qquad
\mathrm{Var}[A] = \frac{\mu(1-\mu)}{\alpha+\beta+1}
\]

The sum \(\alpha + \beta\) is the equivalent number of observations behind the estimate. Knowledge level maps directly to it:

| Knowledge | Prior guidance | Example |
|-----------|----------------|---------|
| Unknown | Pessimistic mean, \(\alpha+\beta\) small | \(\text{Beta}(9, 1)\): \(\mu = 0.9\), standard deviation \(\approx 0.09\) |
| Vendor-attested | Mean below the advertised figure, modest \(\alpha+\beta\) | Mean set under the SLA to reflect unverified claims |
| Observed | Prior updated with measured successes and failures | Updated as in [02](02-risk-model.md) §3.2 |
| Verified | Large \(\alpha+\beta\) | \(\text{Beta}(9999, 1)\): \(\mu = 0.9999\), standard deviation \(\approx 10^{-4}\) |

Because the prior is wide and pessimistic, an unmeasured Vortex raises both tail risk and, where downstream structure is nonlinear, expected risk ([02](02-risk-model.md) §2.3). Measuring it narrows the distribution.

Evidence (`evidence.successes`, `evidence.trials`) may be supplied in the model and is applied with the Beta update.

### 3.3 Consequence

A Vortex declares the consequence of failing its contract, as a distribution in the system impact unit. This is the Vortex's own direct loss. Losses incurred downstream are counted at the downstream nodes.

### 3.4 Uncertain Propagation

How a Vortex failure affects other nodes is often as uncertain as its reliability. Entries in the impact matrix may therefore be probability distributions on \([0,1]\) instead of fixed numbers. They are sampled together with the other epistemic parameters in a single draw ([02](02-risk-model.md) §2.1).

## 4. Interaction with the Rest of the Model

A Vortex participates in Assemblies, success structures (series, redundancy, failover), and the impact matrix exactly as a Subassembly does. The engine does not need its internals; it needs its reliability distribution, its consequence, and its impact weights.

## 5. The Non-Determinism Boundary

A Subassembly operates deterministically while its state stays inside the modeled region. When it leaves that region, it escalates to an inference-class Vortex. The Subassembly's `escalation` block defines the boundary:

| Field | Meaning |
|-------|---------|
| `max_allowable_risk_entropy` | Limit on attribution entropy \(H\) ([03](03-failure-modes.md) §5.1) |
| `vortex_ref` | The Vortex that receives the escalation |
| `mutation_target` | The part of the Subassembly the Vortex may change, normally its impact weights |
| `max_weight_delta` | Optional bound on how far any weight may move in one adaptation |

The boundary acts as a circuit breaker. While \(H \le H_{\max}\), evaluation uses only deterministic mathematics. When \(H > H_{\max}\), the Subassembly's state is passed to the Vortex, which returns a correction \(\Phi\) to the impact matrix:

\[
\mathbf{W}_{\text{adapted}} = \mathbf{W}_{\text{static}} + \Phi(\vec{S}_{\text{downstream}}, \text{Context})
\]

where \(\vec{S}_{\text{downstream}} = \mathbf{W}\vec{F}\) is the current propagated failure vector. The Vortex reads anomalous data, makes an inductive judgment, and returns a matrix modification, which is a runtime re-wiring of the model for the new operating condition.

An engine must treat the returned \(\Phi\) as untrusted input and apply it only after validation:

1. \(\mathbf{W}_{\text{adapted}}\) conforms to the schema (dimensions, numeric type).
2. Every entry lies in \([0, 1]\); entries outside are clipped.
3. If `max_weight_delta` is set, \(|\Delta w_{ji}| \le\) that bound for every entry.
4. The change is recorded with its inputs for audit.

The validated matrix is published as one atomic update ([06](06-drift-control-and-recalibration.md) §3).

## 6. Evaluation State: Laminar and Turbulent

An evaluation (per node and for the whole system) is **Laminar** when it is deterministic and inside validated bounds, and **Turbulent** otherwise. The system is Turbulent if any node is.

An evaluation is Turbulent when any of these holds:

1. The attribution entropy \(H\) of a Subassembly exceeds its `max_allowable_risk_entropy`.
2. The approximation-accuracy confidence \(c\) is below its minimum \(c_{\min}\) ([06](06-drift-control-and-recalibration.md) §4).
3. A Vortex declares a `variance_limit` and \(\mathrm{Var}[A_{\text{vortex}}]\) exceeds it.
4. An inference-class Vortex has produced an adaptation that has not yet been confirmed by a recalibration pass.

Turbulent results are still reported, with the cause listed, because the reported distribution already carries the widened uncertainty. The flag signals that the result should not be treated as a validated deterministic output.

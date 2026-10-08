# 03. Failure Modes

A single reliability figure per component is not enough. A Subassembly has several parallel **failure modes**, each acting as an independent channel with its own capacity, friction, and degradation triggers. This document defines how modes are modeled, how they combine, and how the dominant one is identified. Symbols are in [notation.md](notation.md).

```
                            +--> [ Mode 1: Memory leak ]       slow accumulation
                            |
[ Telemetry inflow ] -------+--> [ Mode 2: Connection starvation ]  rapid spike
                            |
                            +--> [ Mode 3: Storage decay ]     silent drift
```

## 1. Anatomy of a Failure Mode

Each mode in a Subassembly specifies:

| Field | Meaning |
|-------|---------|
| `mechanism` | The Element behavior that produces the failure (§2) |
| `element_ref` | The Element in the Subassembly whose state drives the mode |
| `rupture_threshold` | Normalized saturation ratio in $[0,1]$ at which the mode trips |
| `fragility` | State-driven probability curve: a Weibull in normalized pressure (§3) |
| `baseline_hazard` | Time-driven hazard rate $\lambda_0$, fixed or uncertain, with optional `multiplier` drivers that scale it (see [02](02-risk-model.md) §3.1) |
| `consequence` | Impact if this mode occurs, in the system impact unit |

At least one of `fragility` and `baseline_hazard` is required.

## 2. Mechanisms

The mechanism ties a failure mode to one of the Element types in [01](01-foundations.md).

| Mechanism | Element | Behavior | Example |
|-----------|---------|----------|---------|
| `CapacitiveAccumulation` | Capacitance | Stored quantity rises toward its limit | Memory leak; replication lag filling a staging buffer |
| `ResistiveThrottle` | Resistance | A path constricts, raising local pressure | Connection-pool exhaustion |
| `InductiveMomentumCollapse` | Inductance | Sustained flow stalls, backing up upstream | Thread-pool starvation causing a latency surge |

### 2.1 Examples

**Database tier**

- *Connection pool exhaustion* (`ResistiveThrottle`): the return flow path pinches shut, and local pressure spikes within seconds.
- *Replication lag* (`CapacitiveAccumulation`): the staging buffer fills until the standby is declared unhealthy.

**Compute tier (worker instance)**

- *Memory leak or resource exhaustion* (`CapacitiveAccumulation`): constant inflow; the hazard rate rises as remaining headroom shrinks.
- *Thread-pool starvation* (`InductiveMomentumCollapse`): processing cadence stalls, causing an upstream backup.

## 3. From Pressure to Probability

**Differential integrator.** The pressure (normalized state) of mode $m$ integrates net inflow:

$$
P_m(t) = P_{\text{baseline}} + \int_0^t \left(Q_{\text{degradation}}(\tau) - Q_{\text{leak}}(\tau)\right) d\tau
$$

Flows here are expressed in pressure-rate units, so the factor $K/V$ of the physical accumulator equation ([01](01-foundations.md) §5) is absorbed into $Q$.

**Statistical hazard.** Pressure maps to a failure probability through a Weibull-form curve with scale $\eta$ and shape $\beta_W$:

$$
F_m(P) = 1 - \exp\left(-\left(\frac{P}{\eta}\right)^{\beta_W}\right)
$$

The quadratic form $F_m(P) = 1 - \exp(-k P_m^2)$ is the special case $\beta_W = 2$, $k = \eta^{-2}$.

**Rupture threshold.** The threshold is a hard trip: once the saturation ratio of mode $m$ reaches `rupture_threshold`, the mode is failed and $F_m = 1$ for the remainder of the interval. Below the threshold, $F_m$ is the probability given below.

**Mode probability.** A mode may have a state-driven part (the fragility curve evaluated at the current pressure) and a time-driven part (the baseline hazard, scaled by $D(t)$ as in [02](02-risk-model.md) §3.1). Treating the two mechanisms as independent causes of the same mode,

$$
F_m(t) = 1 - \big(1 - F_m(P_m(t))\big)\big(1 - F_{m,\text{haz}}(t)\big), \qquad
F_{m,\text{haz}}(t) = 1 - \exp\left(-\int_0^t \lambda_0 D(\tau)\,d\tau\right)
$$

omitting whichever factor is not configured. When the same telemetry drives both $D(t)$ and the pressure $P_m$, only one of the two should be configured, to avoid counting that stress twice.

## 4. Competing Risk

A component fails if **any** mode fails. When the modes' failure times are independent, the component survival probability is the product of mode survival probabilities, with $F_m(t)$ the mode probability of §3:

$$
A_{\text{comp}}(t) = \prod_{m=1}^{M}\left(1 - F_m(t)\right)
$$

For hazard-driven modes, $F_m(t) = 1 - \exp\left(-\int_0^t \lambda_m(\tau)\,d\tau\right)$, and the product equals $\exp\left(-\int_0^t \sum_m \lambda_m\,d\tau\right)$, so hazards add. The independence assumption fails when modes interact (one breach accelerating another). Interacting modes are modeled with the cross-coupled probability-flow equation in [05](05-execution-model.md) §4, or by joint simulation.

## 5. Root-Cause Attribution

A rising component hazard is not enough for remediation; the engine must say which mode is responsible. Two quantities are computed per mode.

Each mode has an effective hazard $\lambda_m(t) = \dfrac{dF_m/dt}{1 - F_m(t)}$, which reduces to the configured rate for a purely hazard-driven mode. The unconditional rate at which the mode is currently producing failures is

$$
\frac{dF_m}{dt} = \big(1 - F_m(t)\big)\lambda_m(t)
$$

The **attribution share** is the probability that a failure occurring now is due to mode $m$ (the cause-specific hazard fraction):

$$
\pi_m(t) = \frac{\lambda_m(t)}{\sum_{j=1}^{M}\lambda_j(t)}
$$

The mode with the largest $\pi_m$ or the sharpest acceleration is selected as the root cause, which lets the system pick a deterministic remediation tool without invoking an inference component.

### 5.1 Attribution Entropy

How decisive the attribution is can be measured by the normalized Shannon entropy of $\pi$:

$$
H(t) = -\frac{1}{\ln M}\sum_{m=1}^{M}\pi_m(t)\ln \pi_m(t), \qquad H \in [0, 1]
$$

$H \approx 0$ means one mode clearly dominates and a deterministic tool can act. $H \approx 1$ means failure pressure is spread across modes and the cause is ambiguous. This is the quantity compared against `max_allowable_risk_entropy` at the escalation boundary ([04](04-vortex-black-box-components.md) §5). It is defined for $M \ge 2$; with a single mode, $H = 0$.

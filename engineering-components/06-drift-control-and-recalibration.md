# 06. Drift Control and Recalibration

Interval-driven evaluation ([05](05-execution-model.md) §6) uses fast approximations, and approximation error accumulates. This document specifies how that drift is bounded: a scheduled **recalibration** (re-anchoring) against raw telemetry, a drift-accounting model that prices the error accumulated between recalibrations, and a circuit breaker that acts when confidence falls too low. Symbols are in [notation.md](notation.md).

## 1. The Problem: Compounding Drift

Between recalibrations the engine advances state with fast numerical simplifications (Laplace-domain operators, Fourier or neural operators, linearizations) instead of integrating every raw event. Each simplification introduces a small truncation error. Left uncorrected, these errors compound across intervals, much like a leak in an accumulator, and the simulated state progressively detaches from the real system. The longer the simplified model runs unchecked, the wider the variance of its predictions.

## 2. Recalibration (Re-anchoring)

On a schedule, the engine runs a **recalibration pass**: it suspends the shortcuts for that computation and executes a deterministic calculus-and-probability update directly against the raw, uncompressed telemetry. The result replaces the approximate state.

```
 risk state
     ^
     |        /|                       /|
     |       / |  incremental         / |  incremental
     |      /  |  (drift accrues)    /  |  (drift accrues)
     |     /   *                    /   *
     |    /    re-anchor           /    re-anchor
     +---+-----+------------------+-----+-----------------> time
        t0    t_1                t_2   t_3     (scheduled ticks)
```

Between ticks, drift is allowed to accumulate, but it is **measured** (§4), so the engine always knows how far its approximate state may have wandered.

## 3. Execution Requirements

### 3.1 Decoupling from the Main Loop

The recalibration pass must not run synchronously inside the incremental loop. Processing raw history inside the loop would produce a stop-the-world pause at every tick. The pass runs on an independent schedule as a background computation:

```
INCREMENTAL LOOP (per log interval)
 [log slice] -> [fast operators] -> [live state] -> [log slice] -> ...
                                         ^
                                         | merge result (§3.2)
RECALIBRATION (scheduled, background)    |
 [tick] -> [integrate raw telemetry snapshot] ----------+
```

Benefits:

1. **Bounded incremental latency**: the loop's cost does not grow with the amount of raw history.
2. **Non-blocking publication**: the loop never waits for the heavy pass.
3. **Graceful degradation**: if the background pass is slow or fails, the loop continues on its shortcuts and the drift model records the missed tick (§4.3).

### 3.2 Merging a Result Without Losing Updates

The recalibration pass computes the true state **as of its tick time** $t_a$ from a snapshot of raw telemetry. It finishes at some later time $t_b$. During $[t_a, t_b]$ the incremental loop has kept advancing the live state. Replacing the live state with the pass result would silently discard that progress.

The merge therefore must:

1. Take the pass result (state as of $t_a$).
2. Re-apply the incremental updates for log events in $(t_a, t_b]$ to it.
3. Publish the resulting state, with a drift variance equal to the increments of the replayed updates only (§4.1), not zero.

When no events arrived in $(t_a, t_b]$, the post-merge drift variance is zero.

A conforming way to avoid races is a single-writer rule: only the incremental loop publishes state, and the recalibration pass hands its result over to it. Any approach is acceptable if no update is lost.

### 3.3 Atomic Publication

A published state is a single consistent unit: the state vector, the impact matrix, and the drift variance. Readers must never observe some of these from one update and some from another. Writers prepare the new state completely and then make it visible in one indivisible step. The mechanism is implementation-specific (an atomic reference swap, a lock-protected pointer replacement, or a transactional store), but the observable behavior is not.

## 4. Drift Accounting

Model accuracy is treated as an uncertainty in the same framework as everything else.

### 4.1 Accumulated Error Variance

Each incremental update over an interval $\delta$ adds approximation-error variance

$$
v(\delta) = d_0\,\exp\left(\frac{\delta}{\tau}\right)
$$

where $d_0$ is the base drift variance and $\tau$ the growth time constant (`growth_time_constant_sec`; a typical value is 60 s). Widening the sampling interval raises the cost of each update exponentially. Assuming the errors of successive updates are independent, variances add, so after $n$ updates since the last recalibration

$$
V_{\text{drift}} = \sum_{k=1}^{n} v(\delta_k)
$$

Recalibration resets $V_{\text{drift}}$ to the replayed increments of §3.2. If the errors are positively correlated (a systematic bias), $V_{\text{drift}}$ grows faster than the sum, and the sum underestimates it. Models with a known bias should set $d_0$ conservatively.

### 4.2 Accuracy Confidence

Treating the approximation error $e$ as zero-mean Gaussian with variance $V_{\text{drift}}$, the confidence that it lies within a tolerance $\varepsilon$ (`error_tolerance`, in the units of the state being approximated) is

$$
c = P\big(|e| \le \varepsilon\big) = \operatorname{erf}\left(\frac{\varepsilon}{\sqrt{2\,V_{\text{drift}}}}\right)
$$

with $c = 1$ when $V_{\text{drift}} = 0$. The tolerance and the minimum allowed confidence $c_{\min}$ (`minimum_confidence`) are model parameters.

### 4.3 Circuit Breaker and Missed Ticks

If $c < c_{\min}$, the engine abandons the simplified path and applies the configured `remediation`:

- `ForceDirectIntegration`: run the direct calculus path now, for the affected nodes.
- `EscalateToVortex`: hand the affected state to an inference-class Vortex ([04](04-vortex-black-box-components.md)).

A missed or late recalibration tick needs no special handling: no reset occurs, so $V_{\text{drift}}$ keeps growing, $c$ falls, and the breaker fires if it must. Evaluations made while $c < c_{\min}$ are flagged Turbulent ([04](04-vortex-black-box-components.md) §6). Because confidence is a first-class quantity, drift is never invisible.

## 5. Schedule

The recalibration interval is specified as a **cron expression** (`schedule` in the schema), not as a count of evaluation cycles. The interval is chosen from computational constraints and the accuracy requirement, and the model works incrementally between ticks.

| Aspect | Rule |
|--------|------|
| Syntax | Five fields (`minute hour day-of-month month day-of-week`), or six with a leading `second` field for sub-minute schedules |
| Time base | UTC |
| Scope | A system-level default, with optional per-node override |
| Example | `*/15 * * * *` recalibrates every 15 minutes |

### 5.1 Choosing the Interval

The interval has an upper and a lower bound.

**Upper bound (accuracy).** The confidence must remain at or above $c_{\min}$ until the next tick. From §4.2 this requires

$$
V_{\text{drift}} \le V_{\max} = \frac{\varepsilon^2}{2\,\left[\operatorname{erf}^{-1}(c_{\min})\right]^2}
$$

so the number of incremental updates between ticks is at most $n_{\max} = \lfloor V_{\max} / v(\delta) \rfloor$, and the schedule interval should not exceed about $n_{\max}\,\delta$.

*Example:* $d_0 = 10^{-4}$, $\tau = 60$ s, $\delta = 10$ s, $\varepsilon = 0.05$, $c_{\min} = 0.85$. Then $\operatorname{erf}^{-1}(0.85) = 1.0179$, $V_{\max} = 1.206\times 10^{-3}$, $v(\delta) = 1.181\times 10^{-4}$, $n_{\max} = 10$, so the interval should not exceed about 100 s.

**Lower bound (compute).** A recalibration pass must complete before the next tick, otherwise ticks are missed (§4.3). The interval must exceed the pass's duration, with margin, for the telemetry volume since the last anchor.

The schedule is chosen between those bounds. A longer interval saves compute and raises the drift carried between anchors; a shorter one does the opposite.

## 6. What Recalibration Does and Does Not Guarantee

Recalibration guarantees that the approximation error accumulated by the incremental path before the tick time $t_a$ is removed, provided the pass completes. Combined with an on-time schedule satisfying §5.1, $V_{\text{drift}}$ stays below $V_{\max}$ between ticks, within the independence assumption of §4.1.

It does not:

- remove error inside the interval since the last tick (that is bounded and reported, not eliminated),
- correct errors in the model structure, such as a missing failure mode or a wrong hazard family,
- correct errors in the raw telemetry, or in the direct integration used by the pass itself.

Statements that the system is "free of drift" should be read as "drift is bounded and quantified" under these conditions.

## 7. Schema Representation

Drift control is configured in a single `recalibration` object, used at the system level and optionally overridden per node. Its fields are defined in [`schema/tinkerdiff.schema.json`](schema/tinkerdiff.schema.json), `$defs/RecalibrationPolicy`:

| Field | Meaning |
|-------|---------|
| `schedule` | Cron expression for the recalibration tick (§5) |
| `base_quantization_tier` | Highest deterministic tier used between ticks ([05](05-execution-model.md) §2) |
| `drift_model` | $d_0$ (`base_drift_variance`) and $\tau$ (`growth_time_constant_sec`) of §4.1 |
| `accuracy` | `error_tolerance` $\varepsilon$, `minimum_confidence` $c_{\min}$, and `remediation` (§4.3) |
| `missed_tick_policy` | `accumulate` (default; §4.3) or `run_late` (start the pass as soon as possible after a miss) |

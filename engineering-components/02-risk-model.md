# 02. Risk Model

This document defines how TinkerDiff turns a modeled system into a risk distribution: what risk is, how uncertainty enters, how component probabilities combine, and what an engine reports. Symbols are in [notation.md](notation.md).

The reliability mathematics follows probabilistic risk assessment (PRA) practice from the nuclear industry, including dynamic methods such as Analysis of Dynamic Accident Progression Trees (ADAPT).

## 1. Definition of Risk

Risk is defined by three questions (the Kaplan–Garrick triplet):

1. What can go wrong? Scenarios \(S_i\).
2. How likely is it? Probabilities or frequencies \(p_i\).
3. What are the consequences? Impacts \(x_i\).

TinkerDiff treats \(p_i\) and \(x_i\) as uncertain quantities. For a horizon \(T\), total risk is the random variable

\[
\mathcal{R} = \sum_i B_i\,X_i, \qquad B_i \mid p_i \sim \text{Bernoulli}(p_i)
\]

where \(B_i\) indicates that scenario \(S_i\) occurs within \(T\), and \(X_i\) is its consequence. By linearity of expectation, and assuming each \(p_i\) is independent of its own \(X_i\),

\[
E[\mathcal{R}] = \sum_i E[p_i]\,E[X_i]
\]

This holds without assuming independence between different scenarios. Higher moments and quantiles of \(\mathcal{R}\) do depend on scenario correlation, so engines must preserve it by sampling shared parameters and common-cause events jointly.

### 1.1 Impact Units

Consequences are expressed in the system's declared **impact unit** (`impact_unit` in the schema). Dollars are the intended default, but any quantifiable outcome may be used: lost requests, user-minutes of downtime, safety incidents, or a composite score. All consequences in one model must share one unit. Conversions are the modeler's responsibility and belong in the consequence definition, not in the engine.

Consequences may be per occurrence, or per unit time with a recovery time (for example dollars per hour of outage multiplied by time to recover); both are distributions.

Two equivalent views of the same quantity are supported:

- **Event view:** each scenario has a probability \(p_i\) and a consequence \(X_i\) per occurrence, as above.
- **Availability view:** a component or the whole system has an expected availability \(E[A]\) over horizon \(T\) and a cost rate \(c\) per unit of unavailable time, giving \(E[\mathcal{R}] = c\,(1 - E[A])\,T\). In the schema this is a consequence with basis `per_unit_time` and no recovery time.

### 1.2 Risk Output

An engine reports:

- the **expected value** \(E[\mathcal{R}]\) in the impact unit,
- **quantiles** (for example the median, 95th, and 99th percentiles) of \(\mathcal{R}\),
- optionally a **tail measure** such as conditional value at risk,
- the **epistemic share** of the variance (§2.2).

The output is a distribution, not a single number. A single advertised figure such as "99.95% availability" hides the width of the underlying uncertainty.

## 2. Uncertainty

### 2.1 Aleatory and Epistemic

- **Aleatory** uncertainty is inherent randomness: an instance crash, a bit flip. It is represented by the Bernoulli outcome \(B_i\) and by consequence variability.
- **Epistemic** uncertainty is lack of knowledge: for example an unknown third-party CDN versus a verified tier-1 provider. It is represented by **distributions over parameters** (Beta for probabilities, Lognormal or Gamma for positive quantities), not point estimates. More knowledge means a narrower distribution.

Evaluation is therefore two-level. Sample the epistemic parameters \(\theta\), compute the system's failure probabilities under \(\theta\), then sample outcomes. Repeating this yields the distribution of \(\mathcal{R}\).

### 2.2 Separating the Two

By the law of total variance,

\[
\mathrm{Var}[\mathcal{R}] = E\big[\mathrm{Var}[\mathcal{R}\mid\theta]\big] + \mathrm{Var}\big[E[\mathcal{R}\mid\theta]\big]
\]

The second term is the variance caused by incomplete knowledge. Reporting it separately tells a team how much of the risk could be reduced by measuring, verifying, or replacing a component, as opposed to being inherent.

### 2.3 How Uncertainty Increases Risk

Uncertainty raises reported risk through three mechanisms. Engines and modelers should not assume the first one alone.

1. **Tail widening.** Increasing the variance of an input parameter widens \(\mathcal{R}\), which raises upper quantiles and tail measures even when \(E[\mathcal{R}]\) is unchanged. This is the case for series structures with independent inputs, where the expectation of a product of independent variables is the product of expectations.
2. **Nonlinearity.** When risk is a nonlinear function of an uncertain parameter (redundancy, threshold effects, convex or capped consequences), Jensen's inequality shifts the mean: for convex \(g\), \(E[g(\theta)] \ge g(E[\theta])\). Wider distributions then raise the expected value too.
3. **Conservative priors.** An unknown component's prior is not the vendor's advertised figure. Its mean is set pessimistically for its knowledge level and its effective sample size is small, so evidence has to be accumulated before the distribution narrows (see [04](04-vortex-black-box-components.md) §3).

## 3. Component Failure Probability

### 3.1 Dynamic Hazard Rates

Static analysis assumes a constant failure rate \(\lambda_0\). Real components experience stress that makes the rate time-dependent:

\[
\lambda(t) = \lambda_0 \cdot D(t), \qquad
D(t) = \exp\left(w_{\text{mem}} \cdot M(t) + w_{\text{io}} \cdot I(t) + w_{\text{err}} \cdot \frac{dE}{dt}\right)
\]

with example drivers:

- \(M(t)\): memory pressure (leaks accelerate crash probability),
- \(I(t)\): disk I/O or connection-pool exhaustion (compounding friction),
- \(dE/dt\): error-rate acceleration (cascading starvation).

The schema generalizes this as a list of weighted drivers, each a level, derivative, or integral of a telemetry signal. The probability that a mode has occurred by time \(t\) is

\[
F(t) = 1 - \exp\left(-\int_0^t \lambda(\tau)\,d\tau\right)
\]

### 3.2 Bayesian Updating

Availability or success probability is held as a Beta distribution. When telemetry reports \(k_t\) successes in \(n_t\) windows, conjugate updating gives

\[
\alpha_{t+1} = \alpha_t + k_t, \qquad \beta_{t+1} = \beta_t + (n_t - k_t)
\]

The mean is \(\alpha/(\alpha+\beta)\) and the variance is

\[
\mathrm{Var} = \frac{\alpha\beta}{(\alpha+\beta)^2(\alpha+\beta+1)} = \frac{\mu(1-\mu)}{\alpha+\beta+1}, \quad \mu = \frac{\alpha}{\alpha+\beta}
\]

so \(\alpha+\beta\) acts as an equivalent number of observations, and variance shrinks as evidence accumulates. The update assumes windows are exchangeable. If behavior drifts over time, older evidence should be discounted.

## 4. Combination Rules

Combination rules are the mathematical operators that merge component results according to topology. They are configuration on a Subassembly or a redundancy group, not additional structural units.

| Rule | Use | Formula | Assumption |
|------|-----|---------|------------|
| **Series** (multiplication) | All components required | \(A_{\text{total}} = \prod_i A_i\) | Independent failures |
| **Parallel redundancy** (Boolean AND of failures) | Service fails only if all paths fail | \(F_{\text{total}} = \prod_i F_i\) | Independent failures |
| **\(k\)-of-\(N\)** | Survives while at least \(k\) of \(N\) are healthy | \(A = \sum_{j=k}^{N}\binom{N}{j} a^j (1-a)^{N-j}\) | Identical, independent members with availability \(a\) |
| **Competing modes** (Boolean OR) | Component fails if any mode breaches | See [03](03-failure-modes.md) §4 | Independent mode times |
| **Epistemic convolution** | Merging a measured and an unmeasured component | See §4.2 | Independent inputs |

For non-identical members, the \(k\)-of-\(N\) probability is computed by enumerating or recursing over member subsets.

### 4.1 Common-Cause Failures

Independent redundancy (for example three availability zones) is weakened by shared mechanisms such as a bad control-plane deploy. In the beta-factor model a fraction \(\beta_{\text{CCF}}\) of each member's hazard rate \(\lambda\) is a common event that fails all members at once:

\[
\lambda_C = \beta_{\text{CCF}}\,\lambda, \qquad \lambda_I = (1-\beta_{\text{CCF}})\,\lambda
\]

For a \(k\)-of-\(N\) group over horizon \(T\), with \(a = e^{-\lambda_I T}\),

\[
A_{\text{group}} = e^{-\lambda_C T}\sum_{j=k}^{N}\binom{N}{j} a^j (1-a)^{N-j}
\]

### 4.2 Epistemic Convolution

Combining independent uncertain quantities requires the distribution of the combination, not just its mean. For a sum \(Z = X + Y\) the density is the ordinary convolution. For a product \(Z = XY\), as in a series availability, the density is the multiplicative convolution:

\[
f_Z(z) = \int f_X(x)\, f_Y\!\left(\frac{z}{x}\right)\frac{dx}{|x|}
\]

Equivalently, \(\ln Z\) is the sum \(\ln X + \ln Y\). Engines may evaluate these by Monte Carlo sampling rather than by integration.

## 5. System Structure and Propagation

### 5.1 Top Event

A system declares a **top event** (for example "service unavailable") with two parts:

- a **structure**: success logic over nodes, built recursively from `all` (series), `any` (1-of-N), `k_of_n`, and `failover` operators using the rules of §4, with an optional common-cause factor on an operator;
- a **consequence** of the top event failing.

The availability of each node is its survival probability over the horizon: the competing-risk product over its failure modes for a Subassembly ([03](03-failure-modes.md) §4), or the sampled reliability for a Vortex ([04](04-vortex-black-box-components.md) §3.2). Node availabilities are then combined through the structure.

### 5.2 Propagation

Failure probabilities at one node feed other nodes through the impact matrix \(\mathbf{W}\) ([05](05-execution-model.md) §3.3).

### 5.3 Avoiding Double Counting

Consequences exist at two levels: direct losses attached to a node or failure mode (for example repair cost), and the top-event consequence (for example revenue lost while the service is down). A model should put each loss at exactly one level. Correlated failure across nodes comes from the propagation weights and common-cause factors, and its effect on the distribution of \(\mathcal{R}\) is obtained by joint sampling.

## 6. Comparison with Point-SLA Methods

| Dimension | Point-SLA method | TinkerDiff (dynamic PRA) |
|-----------|------------------|---------------------------|
| Logic | Product of advertised SLAs | Distributions plus minimal cut sets |
| Unknown vs. known provider | Variance ignored | Wide, conservative distribution for unknown components |
| Cross-zone failures | Assumed independent | Common-cause factors |
| Degrading inputs | Binary threshold alerts | Continuous hazard multipliers \(\lambda(t) = \lambda_0 D(t)\) |
| Output | One number | Distribution with expected value and quantiles |

A worked example is in [examples/cloud-service-uptime.md](examples/cloud-service-uptime.md).

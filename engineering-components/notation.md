# Notation and Conventions

Math in this specification is written with `$ … $` for inline and `$$ … $$` for display expressions, which GitHub renders directly. Dollar amounts in prose are escaped as `\$`.

## General

| Symbol | Meaning |
|--------|---------|
| $t$ | time, in seconds unless a field name or symbol says otherwise |
| $\Delta t$ | an evaluation interval (time between two log reads) |
| $T$ | evaluation horizon: the window over which failure probabilities are computed |
| $\vec{x}$ | a vector; bold capitals ($\mathbf{A}, \mathbf{W}$) are matrices |
| $E[\cdot]$, $\mathrm{Var}[\cdot]$ | expectation and variance |
| $\mathbb{1}_{S}$ | indicator: 1 if event $S$ occurs, otherwise 0 |

## Elements (effort/flow)

| Symbol | Meaning |
|--------|---------|
| $e$, $f$ | effort and flow (conjugate pair; power $= e \cdot f$) |
| $C$, $I$, $R$ | capacitance, inductance, resistance coefficients |
| $n$ | transformer ratio |
| $\gamma$ | leak/damping rate of an Element, in 1/s (`damping_leak_coefficient` in the schema) |
| $P$, $Q$, $V$ | pressure, volumetric flow, volume (hydraulic domain) |
| $K$ | bulk modulus |
| $\rho$, $C_d$, $A(\phi)$ | fluid density, discharge coefficient, opening area |

## Risk and reliability

| Symbol | Meaning |
|--------|---------|
| $S_i$, $p_i$, $x_i$ | scenario, its probability, its consequence (Kaplan–Garrick triplet) |
| $X_i$ | consequence as a random variable |
| $\mathcal{R}$ | total risk over the horizon (a random variable) |
| $\lambda$, $\lambda_0$ | hazard rate and its baseline value, in 1/s |
| $D(t)$ | hazard multiplier from degradation drivers |
| $F_m(t)$ | probability that failure mode $m$ has occurred by time $t$ |
| $A_{\text{name}}$ | availability of the named component (always carries a descriptive subscript) |
| $\alpha$, $\beta$ | shape parameters of a Beta distribution |
| $\eta$, $\beta_W$ | Weibull scale and shape |
| $k$-of-$N$ | redundancy rule: the group survives while at least $k$ of $N$ members are healthy |
| $\beta_{\text{CCF}}$ | common-cause fraction (beta-factor model) |

## Propagation and execution

| Symbol | Meaning |
|--------|---------|
| $\mathbf{W}$ | impact (propagation) matrix; entry $w_{ji}$ is the conditional probability that failure input $i$ causes failure at target $j$ |
| $\vec{F}$ | vector of failure-mode probabilities, the input to $\mathbf{W}$ |
| $\mathbf{A}$, $\mathbf{B}$ | state and input matrices of a linear state-space system |
| $A_i$, $B_{ij}$, $R$ | drift (advection) coefficients, diffusion tensor, and reaction rate of the probability-flow equation. These are distinct from the matrices above; context disambiguates |
| $\hat{P}(x,s)$ | Laplace transform of $P(x,t)$ with respect to $t$ |
| $d_0$, $\tau$ | base drift variance and drift growth time constant |
| $V_{\text{drift}}$ | accumulated approximation-error variance since the last re-anchor |
| $\varepsilon$, $c$, $c_{\min}$ | accuracy tolerance, accuracy confidence, and its minimum allowed value |

## Conventions

- **Probabilities** are in $[0, 1]$. Uncertain probabilities are Beta-distributed unless stated otherwise.
- **Impact** is measured in the system's declared impact unit (`impact_unit` in the schema). Dollars are the default, but any quantifiable outcome may be used.
- **Time** values in the schema are in seconds, and field names carry an `_sec` suffix when they are durations.
- **Independence** is assumed wherever a formula multiplies probabilities or adds variances. Each section states this, and correlation is handled through common-cause groups or by sampling.

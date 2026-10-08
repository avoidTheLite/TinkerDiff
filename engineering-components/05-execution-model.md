# 05. Execution Model

This document specifies how a modeled system is evaluated: the mathematical layers, the operators, the cost hierarchy that keeps evaluation cheap, the probability-flow equation and its Laplace-domain solution, and the interval-driven lifecycle. Symbols are in [notation.md](notation.md).

## 1. Mathematical Layers

Every Subassembly is evaluated through three separable layers, each handled by different mathematics:

| Layer | Role | Mathematics | Typical cost |
|-------|------|-------------|--------------|
| **Calculus** | Continuous state: flow rates, degradation trends, hazard multipliers | Derivatives, integrals, ODEs | Low per Element |
| **Statistics** | Failure probabilities, multi-mode overlap, epistemic uncertainty | Distributions, hazard functions, probability-flow equation | Variable |
| **Linear algebra** | Routing of failure effects across the topology | Matrix–vector products | \(O(N^2)\) |

The layers compose: calculus produces state, statistics converts state to probabilities, and linear algebra spreads those probabilities across the system. A non-deterministic component (a Vortex of class `inference`) sits at the boundary of this stack and modifies the linear-algebra layer ([04](04-vortex-black-box-components.md)).

## 2. Cost Hierarchy

Each operation has an approximate computational cost. The engine must use the cheapest tier that clears the decision at hand and must not invoke a more expensive operator when a cheaper one suffices.

```
Tier 1  Boolean operators         O(1)         AND/OR failover checks
Tier 2  Basic algebra             O(N)         degradation multipliers
Tier 3  Linear algebra (mesh)     O(N^2)       matrix-vector propagation (O(N^3) for matrix factorization or exponentials)
Tier 4  Calculus / PDE operators  variable     probability-flow compilation
Tier 5  Vortex inference          highest      agent inference, token generation
```

Deterministic frameworks are built from Booleans upward in this way. The schema field `base_quantization_tier` (values `Boolean`, `Algebraic`, `MatrixMesh`, `NumericalPDE`) declares the highest deterministic tier a node uses between recalibrations. Tier 5 is reached only through the escalation boundary.

## 3. Operators

### 3.1 DiffIntegrator (calculus)

Tracks the continuous pressure (normalized state) of a failure mode:

\[
P_m(t) = P_{\text{baseline}} + \int_0^t \left(Q_{\text{degradation}}(\tau) - Q_{\text{leak}}(\tau)\right) d\tau
\]

Defined in [03](03-failure-modes.md) §3. The integrator named in the schema (Euler, Runge–Kutta 4, or Verlet) and its time step determine numerical accuracy.

### 3.2 StatisticalHazard (statistics)

Converts pressure to a failure probability:

\[
F_m(P) = 1 - \exp\left(-\left(\frac{P}{\eta}\right)^{\beta_W}\right)
\]

Defined in [03](03-failure-modes.md) §3.

### 3.3 MatrixMesh (linear algebra)

Propagates failure probabilities along the topology. Let \(\vec{F}\) be the vector of failure probabilities of a node's modes (the mesh input) and \(\mathbf{W}\) the impact matrix whose rows correspond to target nodes and whose columns correspond to inputs:

\[
\vec{S}_{\text{downstream}} = \mathbf{W}\vec{F}
\]

Each entry \(w_{ji}\) is the conditional probability that failure input \(i\) causes failure at target \(j\), and lies in \([0,1]\). Entries may be probability distributions on \([0,1]\) when the effect is uncertain ([04](04-vortex-black-box-components.md) §3.4); they are sampled with the other epistemic parameters.

Two propagation modes are defined:

| Mode | Formula | Use |
|------|---------|-----|
| `linear` (default) | \( S_j = \min\left(1, \sum_i w_{ji}F_i\right) \) | Small probabilities; cheapest |
| `noisy_or` | \( S_j = 1 - \prod_i \left(1 - w_{ji}F_i\right) \) | Independent causes at larger probabilities |

The linear form is the first-order approximation of the noisy-OR form and agrees with it when every \(w_{ji}F_i\) is small. Without the clamp, the linear sum can exceed 1, so clamping is required.

A matrix-vector product replaces nested conditionals: changing the weights of \(\mathbf{W}\) rewires how pressure in one failure mode applies to adjacent modes across the topology.

### 3.4 Vortex Adaptation (non-deterministic boundary)

When the escalation condition holds, an inference-class Vortex returns a correction to \(\mathbf{W}\):

\[
\mathbf{W}_{\text{adapted}} = \mathbf{W}_{\text{static}} + \Phi(\vec{S}_{\text{downstream}}, \text{Context})
\]

Validation and publication rules are in [04](04-vortex-black-box-components.md) §5.

## 4. Probability-Flow Equation

When failure modes interact continuously, their joint probability density over state variables \(\vec{x}\) (for example memory and connection saturation ratios) evolves as an advection–diffusion–reaction equation, derived from the Fokker–Planck / Kolmogorov forward equation:

\[
\frac{\partial P}{\partial t} =
-\sum_i \frac{\partial}{\partial x_i}\left[A_i(\vec{x}, t)\,P\right]
+ \sum_i \sum_j \frac{\partial^2}{\partial x_i \partial x_j}\left[B_{ij}(\vec{x}, t)\,P\right]
- R(\vec{x}, t)\,P
\]

- **Advection** \(A_i\): deterministic drift of the state, such as a leak trajectory, pushing probability mass toward a failure boundary.
- **Diffusion** \(B_{ij}\): stochastic and epistemic spread. It equals \(\tfrac{1}{2}\sigma\sigma^{T}\) for an underlying noise matrix \(\sigma\), which is why no factor of \(\tfrac{1}{2}\) appears. A larger \(B\) (less knowledge, for example an unmeasured dependency) produces thicker tails.
- **Reaction** \(R\): a first-order rate. \(R > 0\) removes density locally, and \(R < 0\) creates it. Interaction between modes (one breach accelerating another) appears as cross-coupling: with one density per mode, the reaction term is a matrix whose off-diagonal entries move density between modes.

The failure probability over a horizon is the probability mass that has crossed the failure boundary \(\Omega_{\text{fail}}\) (the rupture thresholds of [03](03-failure-modes.md)), for example by treating the boundary as absorbing:

\[
F(T) = 1 - \int_{\Omega_{\text{safe}}} P(\vec{x}, T)\,d\vec{x}
\]

### 4.1 Cheap Solution Strategy

Rather than grid integration of the full equation, the engine decouples the equation into independent one-dimensional channels by separation of variables or the method of characteristics, solves each with lightweight calculus, and recombines the channels through the mesh \(\mathbf{W}\). This is exact only when the cross-coupling is absent or can be diagonalized. For strong coupling the decoupling is an approximation, and its error is part of what the drift model ([06](06-drift-control-and-recalibration.md)) accounts for.

### 4.2 Laplace-Domain Operator

For a single state dimension with constant coefficients \(A\), \(B > 0\), \(R\), the equation is

\[
\frac{\partial P}{\partial t} = -A\frac{\partial P}{\partial x} + B\frac{\partial^2 P}{\partial x^2} - R\,P
\]

Applying the Laplace transform in time, \(\hat{P}(x,s) = \mathcal{L}\{P(x,t)\}\), turns \(\partial P/\partial t\) into \(s\hat{P}(x,s) - P(x,0)\):

\[
s\hat{P}(x,s) - P(x,0) = -A\frac{\partial \hat{P}(x,s)}{\partial x} + B\frac{\partial^2 \hat{P}(x,s)}{\partial x^2} - R\,\hat{P}(x,s)
\]

Rearranged, this is an ordinary second-order differential equation in \(x\) with the initial state as the forcing term:

\[
B\frac{d^2\hat{P}}{dx^2} - A\frac{d\hat{P}}{dx} - (s+R)\,\hat{P} = -P(x,0)
\]

Its characteristic equation \(Br^2 - Ar - (s+R) = 0\) has roots

\[
r_{\pm} = \frac{A \pm \sqrt{A^2 + 4B(s+R)}}{2B}
\]

For an unbounded domain with a bounded solution (\(s + R > 0\)), the solution for initial state \(P(\xi,0)\) is

\[
\hat{P}(x,s) = \int g(x,\xi;s)\,P(\xi,0)\,d\xi, \qquad
g(x,\xi;s) = \frac{1}{\sqrt{A^2+4B(s+R)}}
\begin{cases}
e^{r_-(x-\xi)} & x > \xi \\
e^{r_+(x-\xi)} & x < \xi
\end{cases}
\]

The prefactor follows from the jump condition \(B[\partial g/\partial x]_{x=\xi} = -1\), since \(B(r_+ - r_-) = \sqrt{A^2+4B(s+R)}\).

**Scope and cost.** The transform removes the time dimension from the equation, but producing the state at the end of the interval requires an inverse Laplace transform of \(\hat{P}(x,s)\), either analytic or numerical (for example the Talbot or Stehfest methods). It is a direct, non-iterative evaluation, not an instantaneous one. For constant coefficients the time-domain answer is also available in closed form: for a point mass at \(\xi\),

\[
P(x,t) = \frac{e^{-Rt}}{\sqrt{4\pi B t}}\exp\left(-\frac{(x-\xi-At)^2}{4Bt}\right)
\]

which engines should use as the reference result in that case and as a test oracle for the transform-based path. The Laplace route is of practical value when coefficients are piecewise constant over a log interval, when boundary conditions are imposed, or when operators are composed in the transform domain. Coupled multi-mode systems require matrix-valued \(A\), \(B\), \(R\) and hold only if these can be simultaneously diagonalized; otherwise numerical solution is required.

**Learned operators.** A physics-informed neural operator (PINO) may stand in for the transform path, mapping the log history and \(\Delta t\) to the end-of-interval state in one pass. It is an approximation, and its error must be modeled by the drift model rather than assumed zero.

## 5. Remediation Routing Gate

Beyond risk calculation, the engine decides how to respond to degradation. The routing decision is itself a component, blending deterministic pressure with a statistical classification.

**Step 1: contextual pressure** (calculus, \(O(1)\)):

\[
P_{\text{system}}(t) = w_1 \cdot \frac{d(\text{Error Rate})}{dt} + w_2 \cdot (\text{Latency}) + w_3 \cdot \int_0^t \text{Memory Pressure}\,dt
\]

The weights \(w_i\) absorb the units of their terms, so inputs should be normalized. The integral grows without bound over a long run, and in practice it is taken over a window or with a leak term.

**Step 2: statistical adjustment.** When the entropy condition of [04](04-vortex-black-box-components.md) §5 holds, routing over structural assets (diagnostic prompts, tools, knowledge bases) is a softmax distribution:

\[
P(\text{Asset}_i \mid \text{Telemetry}) = \frac{e^{P_{\text{system}} \cdot \alpha_i + \mu_i}}{\sum_j e^{P_{\text{system}} \cdot \alpha_j + \mu_j}}
\]

- \(\alpha_i\): deterministic scaling factor of the asset.
- \(\mu_i\): bias learned and updated by the inference component.

Implementations should compute the softmax in a numerically stable form (subtract the maximum exponent before exponentiating).

**Step 3: routing outflows.**

- Low entropy and steady pressure: route to deterministic tools (scripts). Calculus is far cheaper than inference.
- High entropy or anomalous spikes: route to inference-class Vortices (diagnostic prompts, knowledge-base scans).

## 6. Interval-Driven Evaluation

The model does not refresh continuously. It runs against a series of logged events, at a defined interval or on demand for a specific operation. Continuous differential equations are thereby reduced to discrete snapshot updates, which enable the closed-form and operator shortcuts above.

### 6.1 Evaluation Lifecycle

```
[ Interval trigger or on-demand request ]
              |
              v
 1. Ingest log slice(s) covering Δt
              |
              v
 2. Route through the cheapest sufficient tier (Boolean, then algebraic hazards)
              |
              v
 3. Incremental update: closed-form / Laplace-domain operators advance failure-mode state
    and add to the accumulated drift variance
              |
              v
 4. Update the mesh: propagate state vectors downstream through W
              |
              v
 5. Check drift confidence and attribution entropy
        confidence < minimum -> fall back to direct integration or escalate
        entropy > limit      -> escalate to the inference-class Vortex
              |
              v
 6. Publish the new state as one consistent snapshot and report the risk distribution
```

Recalibration against raw telemetry is **not** a step of this loop. It runs on its own schedule and merges its result into the live state, as described in [06](06-drift-control-and-recalibration.md).

### 6.2 Requirements for Engines

- The incremental loop must run in bounded time independent of how much raw history exists.
- State readers must always observe a consistent snapshot (state vector, impact matrix, and drift variance from the same update), never a partially applied one.
- Results must be reproducible for a given model, input log, and random seed, except where an inference-class Vortex is invoked; those invocations are recorded.

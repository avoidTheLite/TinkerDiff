# 01. Foundations: Elements and the Effort–Flow Framework

This document defines the atomic unit of the model (the Element), the shared mathematics behind all Elements, and how Elements compose into Subassemblies and systems. Symbols are defined in [notation.md](notation.md).

## 1. Thesis

Components in physical, electrical, mechanical, and software domains share a small set of governing equations. They differ in the dimensional constants of their medium, not in structure. TinkerDiff therefore represents every component with the same base formulas plus configurable scaling parameters.

A component in this framework has:

- a defined **input** and **output** (it may be any process, including a program),
- an internal behavior given by a **base formula** and **scaling parameters**,
- membership in a group of components that share the same mathematical base.

Composition proceeds in four levels: **Elements** (base formulas) combine into **Subassemblies** (real components), which are grouped with **Vortices** into **Assemblies**, which make up the **System**. Components whose internals are unknown are **Vortices** ([04](04-vortex-black-box-components.md)).

### 1.1 Why Closed-Form Evaluation Is Possible

When Elements are linear, or can be linearized about an operating point, a Subassembly reduces to a linear state-space system:

$$
\dot{\vec{x}}(t) = \mathbf{A}\vec{x}(t) + \mathbf{B}\vec{u}(t)
$$

The solution over an interval $[t_0, t]$ is

$$
\vec{x}(t) = e^{\mathbf{A}(t-t_0)}\vec{x}(t_0) + \int_{t_0}^{t} e^{\mathbf{A}(t-\tau)}\mathbf{B}\vec{u}(\tau)\,d\tau
$$

and for input held constant over an interval $\Delta t$, with $\mathbf{A}$ invertible,

$$
\vec{x}(t_0+\Delta t) = e^{\mathbf{A}\Delta t}\vec{x}(t_0) + \mathbf{A}^{-1}\left(e^{\mathbf{A}\Delta t} - \mathbf{I}\right)\mathbf{B}\vec{u}
$$

This replaces step-by-step simulation or learned inference with a single matrix operation per interval. Nonlinear Elements (for example an orifice) require linearization or numerical integration, and the approximation error this introduces is tracked by the drift model in [06](06-drift-control-and-recalibration.md).

## 2. Effort and Flow

In every physical domain, power is the product of two conjugate variables:

$$
\text{Power} = \text{Effort} \times \text{Flow}
$$

- **Effort** $e$: the driving quantity (pressure, voltage, force, data backlog).
- **Flow** $f$: the rate of movement (volumetric flow, current, velocity, throughput).

In software and informational domains, the product $e \cdot f$ is an analogy, not a conserved physical power. Engines must not enforce an energy balance across informational Elements unless the model explicitly declares one.

## 3. The Four Element Types

Every Element manipulates effort and flow in one of four ways:

```
            [ Element types ]
     /          |              |             \
 Capacitance  Inductance   Resistance    Transformer
 stores       stores       dissipates    converts between
 effort       flow         energy        domains or scales
```

| Type | Hydraulic | Electrical | Mechanical (force–velocity) | Software / informational | Base relation |
|------|-----------|------------|-----------------------------|--------------------------|---------------|
| **Capacitance** (C): stores effort | Pressurized chamber / tank (stores pressure) | Capacitor (stores voltage) | Spring (stores force); leaky C ↔ series spring–damper | Database, queue (stores backlog) | $e = \frac{1}{C}\int f\,dt$ |
| **Inductance** (I): stores flow | Fluid inertance (maintains flow) | Inductor (maintains current) | Mass, flywheel (maintains velocity) | Processing buffer (maintains execution momentum) | $f = \frac{1}{I}\int e\,dt$ |
| **Resistance** (R): dissipates / shapes flow | Orifice, valve, calibrated leak | Resistor (voltage drop) | Damper, friction (force drop) | Network latency, drop rate (limits throughput) | $e = R\,f$ (default `linear` form; see §5.1) |
| **Transformer** (TF): converts domains or scales | Pump (mechanical to fluid) | Ideal transformer / gear ratio | Lever, gearbox | API gateway, serializer (format change) | $e_2 = n\,e_1,\quad f_1 = n\,f_2$ |

The transformer relation conserves power: $e_2 f_2 = n e_1 f_2 = e_1 f_1$.

Differences between, say, a hydraulic pump and a battery lie only in the units and constants of their domain. A change in one domain's state vector maps into another's through a linear transformation. This is the basis of bond-graph modeling and unified physical-systems theory.

### 3.1 Leak and Saturation

Real storage Elements dissipate and are bounded. Each Element may carry:

- a **leak/damping rate** $\gamma \ge 0$ (1/s), modifying the state equation as in §6,
- a **capacity limit**, so the state can be reported as a normalized saturation ratio in $[0, 1]$. Failure-mode thresholds ([03](03-failure-modes.md)) are expressed against this ratio.

## 4. Composition

| Level | Definition | Adds |
|-------|------------|------|
| **Element** | One base relation with its parameters and initial state | Dynamics |
| **Subassembly** | Interconnected Elements representing one real component | Internal topology, failure modes, downstream impact weights, escalation boundary |
| **Vortex** | Black-box component standing in for a Subassembly or a whole system | I/O contract, mandatory uncertainty distribution ([04](04-vortex-black-box-components.md)) |
| **Assembly** | Subassemblies and Vortices with the Fittings between them | Success logic (series, redundancy, failover) giving the Assembly's availability |
| **Fitting** | Adapter between two interfaces (Element, Subassembly, or Vortex) | Unit, domain, or shape conversion; a Fitting with a ratio is a transformer relation applied at an interface |
| **System** | One or more Assemblies, plus cross-Assembly Fittings | Top event, impact unit, evaluation policy, recalibration schedule |

An Element of type Transformer models a domain change that is part of the physics of a component. A Fitting is the structural connection that carries such conversions between components. Fittings that carry a ratio use the same relation, $e_2 = n e_1,\ f_1 = n f_2$.

## 5. Worked Example: Pressurized Chamber Circuit

A closed hydraulic circuit with a source, a pressurized chamber, a control valve, and a leak is the reference **equivalent model**. Physical names here label *roles* (what the block does), not full thermo-fluid products. Heat transfer and medium-property detail are intentionally omitted.

**Pressurized chamber (simplified accumulator assembly).** A Capacitance Element with optional leak $\gamma$: fixed geometric volume $V$, bulk modulus $K$, capacitance $C = V/K$. Net inflow raises pressure; $\gamma$ dissipates it. Closest mechanical dual of the leaky chamber is a **series** spring–damper (Maxwell): storage plus relaxation under shared effort — not a parallel Kelvin–Voigt `SpringDamper`.

$$
\frac{dP}{dt} = \frac{K}{V}\left(Q_{\text{in}}(t) - Q_{\text{valve}}(P) - Q_{\text{leak}}(P)\right)
$$

With $e=P$, $f=Q_{\text{net}}$, and $\gamma$ absorbing the leak channel, this is the Capacitance update in §6. Analogy baselines and OpenModelica comparisons live in [analogies/](analogies/).

**Valve (variable resistance).** One of the Resistance forms in §5.1; the orifice form is shown here. Opening area $A(\phi)$ depends on a control variable $\phi$ such as activity frequency:

$$
Q_{\text{valve}} = C_d \cdot A(\phi) \cdot \sqrt{\frac{2\,\Delta P}{\rho}}, \qquad \Delta P \ge 0
$$

For $\Delta P < 0$ the flow reverses: $Q = -C_d A(\phi)\sqrt{2|\Delta P|/\rho}$, or zero if a `check` Resistance form is used.

**Committed volume.** The volume passed to a downstream chamber over an interval is the net of valve flow and leakage:

$$
V_{\text{committed}} = \int_{t_0}^{t_1} Q_{\text{valve}}(t)\,dt - \int_{t_0}^{t_1} Q_{\text{leak}}(t)\,dt
$$

The same structure (a source, a storage Element with a leak, and a variable resistance) describes a memory pool with a garbage collector and a request throttle, risk pressure with alarm recovery, or a battery with a regulator. [examples/learning-simulator.md](examples/learning-simulator.md) maps it to behavioral reinforcement.

### 5.1 Resistance Forms (Scaling and Filtering)

The default Resistance relation is linear, $e = R\,f$. Models may select a **resistance form** so the same Element type covers several useful nonlinear laws. Forms act as amplitude or rate shapers — analogous to soft high/low-pass behavior when composed with Capacitance — without inventing new Element types. The catalog is [`analogies/resistance-forms.json`](analogies/resistance-forms.json).

| Form id | Governing idea | When it is useful |
|---------|----------------|-------------------|
| `linear` | $e = R\,f$ (Ohm / viscous damper) | Proportional drop; closed-form RC/RL with C or I; default for reliability trees |
| `orifice` | $f = C_d A\,\mathrm{sign}(e)\sqrt{2|e|/\rho}$ | Small drives pass little flow; large spikes open up (amplitude-dependent gate) |
| `check` | `linear` or `orifice` with $f \ge 0$ only | One-way habit lock, diode-like escalation, no backflow |
| `deadzone` | $f=0$ for $\|e\| < e_0$, else linear/orifice | Ignore noise below a threshold; alarm only after material pressure |
| `saturation` | $\|f\| \le f_{\max}$ on a linear/orifice core | Hard capacity / rate limit on throughput |
| `power_law` | $f = k\,\mathrm{sign}(e)\,|e|^{\alpha}$ | Tunable sensitivity ($\alpha<1$ compressive, $\alpha>1$ expansive) |

**Statistical / standard labels** for choosing a form (see the JSON `selection_hints`): Gaussian or small-signal regimes → `linear`; heavy-tailed or bursty spikes → `orifice` or `power_law` with $\alpha<1$; rare threshold crossings → `deadzone` (related to peaks-over-threshold thinking); hard SLOs / caps → `saturation`; irreversible transitions → `check`.

Nonlinear forms require linearization or numerical integration about an operating point; the drift model in [06](06-drift-control-and-recalibration.md) tracks the approximation error. Engines that only implement `linear` must reject other forms or treat them as out of scope for that engine version.

### 5.2 Port Direction and Sign Conventions

Every one-port Element (R, C, I) has two ports. Signs are locked as follows so Assemblies do not transpose effort and flow:

| Symbol | Definition |
|--------|------------|
| Port `p` (upstream) | Connection toward the higher-potential / source side of the branch |
| Port `n` (downstream) | Connection toward the lower-potential / sink side of the branch |
| Branch effort | $e := e_p - e_n$ |
| Branch flow | $f > 0$ means flow through the Element from `p` to `n` |
| Leak $\gamma$ | Dissipates stored state; does not reverse port orientation |

For Transformers (two-port):

| Symbol | Definition |
|--------|------------|
| Side 1 | Primary / input port pair |
| Side 2 | Secondary / output port pair |
| Ratio $n$ | $e_2 = n\,e_1$ and $f_1 = n\,f_2$ with $n > 0$ |
| Power | $e_1 f_1 = e_2 f_2$ (positive into side 1 equals positive out of side 2 under this $f$ orientation) |

Fittings that carry a ratio use the same $n$ convention. Engines must reject connections that leave port polarity unspecified when both ends declare ports. Closest OpenModelica one-port baseline uses the same $e = v_p - v_n$, $f = i_p$ orientation; TinkerDiff’s transformer omits Modelica’s leading minus on $i_2$ by defining $f_2$ positive *out* of side 2.

## 6. Element Interface (Language-Neutral)

Every Element exposes the same interface. Implementations may be classes, structs, or tables, provided they satisfy it.

| Part | Content |
|------|---------|
| Parameters | One coefficient ($C$, $I$, $R$, or $n$); for Resistance, optional `resistance_form` (default `linear`); optional leak rate $\gamma$; optional capacity limit |
| State | Effort $e$ and flow $f$, with initial values |
| Ports | Upstream `p` and downstream `n` with the sign rules in §5.2 |
| Inputs | Upstream effort and flow |
| Update | A function of (state, inputs, $\Delta t$) returning new state |
| Outputs | Effort and flow passed downstream, and the normalized saturation ratio |

Continuous-time relations for the ideal linear cores, including the optional leak/damping term $\gamma$:

$$
\text{R (linear): } e = R\,f \qquad
\text{C: } \dot{e} = \frac{f}{C} - \gamma e \qquad
\text{I: } \dot{f} = \frac{e}{I} - \gamma f \qquad
\text{TF: } e_2 = n\,e_1,\ f_1 = n\,f_2
$$

Other Resistance forms replace the linear R law as specified in §5.1; C, I, and TF cores stay as above.

With $\gamma = 0$ these reduce to the base relations in §3. For $f = 0$ the capacitive state decays as $e(t) = e(0)e^{-\gamma t}$, the forgetting-curve behavior used in [examples/learning-simulator.md](examples/learning-simulator.md).

A single explicit-Euler step of length $\Delta t$, the reference discretization for conformance, is

$$
e_{k+1} = e_k + \Delta t\left(\frac{f_k}{C} - \gamma e_k\right), \qquad
f_{k+1} = f_k + \Delta t\left(\frac{e_k}{I} - \gamma f_k\right)
$$

Engines may use higher-order integrators (the schema names Euler, Runge–Kutta 4, and Verlet) but must reproduce the reference values within the tolerance stated in each conformance vector.

```
[ upstream effort, flow ]
            |
   [ Element update: R, C, I, TF relation ]
            |
   [ Fitting: unit / domain conversion ]
            |
[ downstream effort, flow ]
```

## 7. Structure and Parameters

A system model is specified in two layers:

1. **Structural blueprint (topology).** Which components connect to which. It may be imported from an architecture document such as a UML component diagram.
2. **Parameter objects.** Off-diagram data that holds the physics, distributions, and attributes that do not fit in a diagram. The hydration step that joins the two is described in [07](07-specification.md).

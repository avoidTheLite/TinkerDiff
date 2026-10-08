# Example: Learning Simulator (Behavioral Reinforcement Model)

A non-infrastructure example of the TinkerDiff element model: repeated behaviors reinforce their own pathways, and the resulting dynamics are expressed as a hydraulic network of Elements. It shows that the same mathematics used for site-reliability modeling applies to a cognitive system.

Prerequisites: [01 Foundations](../01-foundations.md) (effort/flow, the four Element types).

---

## 1. Problem Statement

Repeated activity amplifies its own pathway. The longer and more frequently a behavior is performed, the more it dominates system state; skills learned in one domain lower the cost of adjacent ones. Behaviors that feed back into their own recurrence include somatic feedback (smiling), metabolic feedback (exercise), social feedback (conversational practice), and chemical feedback (addictive substances, highly rewarding foods).

A usable model must provide:

- **Graded score modifiers.** The effect of an activity is a gain applied to a node, not an on/off switch.
- **Frequency response.** Repeated high-rate signals lower the threshold for re-triggering.
- **Steady states and damping.** Without input, pathways decay to baseline (forgetting, habituation).
- **Closed-form computability.** The state should be computable with ordinary linear algebra and differential equations rather than iterative inference.

## 2. State-Space Reinforcement Matrix

The state of all habits and skills is a vector \(\vec{S}_t\), advanced by a transition matrix \(A\) (structural pathways between behaviors) and an input matrix \(B\) applied to the currently active behaviors \(\vec{u}_t\):

\[
\vec{S}_{t+1} = A\vec{S}_t + B\vec{u}_t
\]

Each node is a damped second-order system, so that state changes are bounded and gradual rather than instantaneous resets or unbounded spikes:

\[
m\frac{d^2x}{dt^2} + b\frac{dx}{dt} + kx = F(t)
\]

with natural frequency \(\omega_n = \sqrt{k/m}\) and damping ratio \(\zeta = b / (2\sqrt{km})\).

For a sinusoidal drive \(F(t) = F_0 \sin(\omega t)\), the steady-state amplitude is

\[
|X(\omega)| = \frac{F_0}{\sqrt{(k - m\omega^2)^2 + (b\omega)^2}}
\]

which peaks near \(\omega = \omega_n\), where \(|X| \approx F_0 / (b\,\omega_n)\) for light damping.

Interpretation:

- **Isolated or off-resonance input.** Damping absorbs the drive; amplitude stays small and the behavior does not persist.
- **Input repeating near \(\omega_n\)** (practice at the cadence the pathway responds to). The node resonates and amplitude grows, which is the condition under which the model commits a permanent pathway.

Here "frequency" means how often the behavior is repeated. High-frequency repetition is not sufficient by itself: above \(\omega_n\) the response amplitude falls off as \(1/\omega^2\). The model therefore requires repetition cadence to be matched against each pathway's \(\omega_n\), which is a parameter of the node.

### 2.1 Cross-Domain Skill Transfer

A learner rarely starts with an empty matrix. Existing low-damping, high-gain sub-routines (spatial awareness, pattern recognition) already exist as resonant branches, so a new task's input vector \(\vec{u}\) couples into established structure through the off-diagonal terms of \(A\), shortening the build-up phase.

## 3. Hydraulic Element Mapping

The reinforcement matrix is realized as a manifold of compressible fluid (neural resources, attention). Performing an activity is a source forcing fluid into a pathway.

| Hydraulic part | Element type | Behavioral role |
|----------------|--------------|-----------------|
| Variable-displacement pump | Source (boundary input \(\vec{u}\)) | Forces volume into the network; displacement scales with task intensity and frequency |
| Gas-charged accumulator | Capacitance (C) | Short-term staging area; absorbs high-pressure spikes and stores elastic energy |
| Flow control valve | Resistance (R), variable | Gating/attention; opening area grows with activity frequency |
| Fluid reservoir | Capacitance (C), large reference volume | Baseline pool of unallocated resources |
| Check valve | Resistance (R), one-way | Habit lock; prevents backflow once a threshold is crossed |
| Calibrated leak | Leak term \(\gamma\) on a Capacitance | Forgetting curve; drains unreinforced volume back to the reservoir |

```
[ Active Behavior (Pump) ] ---> high pressure / compression
                                    |
                             [ Valve ]        <--- activity frequency widens the opening
                                    |
                                    v
                        [ Structural Chamber ] <--- sleep commits retained volume
                                    |
                                    v
                             [ Damping Leak ]  <--- passive decay
```

### 3.1 Compressibility and the Struggle Phase

A new activity has a narrow pathway: fluid compresses and local pressure builds. The bulk modulus \(K\) measures resistance to compression:

\[
K = -V\frac{\Delta P}{\Delta V}
\]

High \(\Delta P\) with low \(\Delta V\) corresponds to effortful practice with little volume reaching the downstream chamber. Accumulated pressure is the score modifier; crossing a pressure threshold triggers channel expansion.

### 3.2 Frequency Response of the Valve

- **Low frequency.** The valve opens briefly, a small volume enters, and it bleeds out through the leak.
- **High frequency.** Sustained input holds the valve open, flow shifts from compressed/turbulent to high-volume laminar, and the pathway's volumetric capacity permanently expands.

The governing relations are the accumulator and orifice equations in [01 Foundations §5](../01-foundations.md).

### 3.3 Steady States and Viscosity

Every chamber leaks at a characteristic rate.

- Highly reinforcing substances behave like low-viscosity fluids: they fill chambers quickly with little resistance.
- Difficult skills behave like high-viscosity fluids: they require sustained pressure to move, but once a chamber fills it drains slowly (high stability).

## 4. Staging and Commit Model

While active, the network is a high-pressure streaming system whose state is provisional (the staging area). Sleep acts as a commit step:

- **Prune.** Chambers where fluid compressed but never reached steady flow are discarded.
- **Commit.** Chambers that sustained high pressure and volume are structurally expanded, updating the persistent baseline.

In model terms, only reinforced pathways survive a commit cycle, which maps to a periodic re-baselining of persistent state from accumulated provisional state. This is the same structure as the clock-driven recalibration in [06 Drift Control](../06-drift-control-and-recalibration.md).

## 5. Why This Example Matters to the Framework

1. Every part (pump, valve, chamber, leak) is an Element with a base formula and scaling parameters.
2. The equations are dimensionally the same as those for electrical, mechanical, and software systems; only the constants differ.
3. Elements compose into Subassemblies and systems.
4. Because the system is a set of ordinary differential equations, its state can be computed directly (see [05 Execution Model](../05-execution-model.md)) rather than by repeated inference.

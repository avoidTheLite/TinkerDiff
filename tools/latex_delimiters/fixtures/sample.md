# Sample Document

Recall that the risk profile for overlapping failure modes (e.g., \(x_{1}\) = Memory Saturation)
is governed by an Advection-Diffusion-Reaction PDE:

\[\frac{\partial P}{\partial t}=-A\frac{\partial P}{\partial x}-R\cdot P\]

Padded inline math such as \( e = R\,f \) is trimmed, and a multi-line display block is kept as is:

\[
B\frac{d^2\hat{P}}{dx^2} - A\frac{d\hat{P}}{dx} - (s+R)\,\hat{P} = -P(x,0)
\]

A LaTeX line break must survive inside display math:

\[
a = 1 \\[2pt]
b = 2
\]

| Symbol | Meaning |
|--------|---------|
| \(\lambda\) | hazard rate |

Costs such as \$10,000 per hour use an escaped dollar sign and are not math.

Code is never converted. Inline code: `\( x \)` and `\[ y \]`.

```
\( not math in a fence \)
\[ nor this \]
```

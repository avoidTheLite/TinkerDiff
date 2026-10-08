# Example: Cloud Service Uptime (SRE)

A worked risk calculation for a three-tier cloud service, showing a Vortex with an epistemic distribution, a \(k\)-of-\(N\) compute tier, a failover database tier, and the resulting risk distribution in dollars. The machine-readable model is [`../schema/examples/cloud-service.json`](../schema/examples/cloud-service.json). The figures below are reproduced in [`../conformance/vectors.json`](../conformance/vectors.json).

Prerequisites: [02 Risk Model](../02-risk-model.md), [04 Vortex Components](../04-vortex-black-box-components.md).

## 1. Topology

```
 [ CDN edge ]            Vortex (external provider)
      |
 [ AZ1 | AZ2 | AZ3 ]     3 availability zones, each: Lambda agent runner + EC2 worker
      |                  Subassemblies in a 2-of-3 redundancy group
 [ DB primary + standby ]  Subassembly with failover
```

All three tiers are required in series. The service is unavailable if the CDN is, if fewer than two zones are healthy, or if the database tier is down.

## 2. Tier Models

### 2.1 CDN Tier (Vortex)

The CDN is an external provider whose internals are not modeled. Its availability is a Beta distribution whose width depends on how much is known:

\[
A_{\text{CDN}} \sim \text{Beta}(\alpha, \beta)
\]

| Case | Distribution | Mean | Standard deviation |
|------|--------------|------|--------------------|
| Unknown vendor | \(\text{Beta}(9, 1)\) | 0.9 | 0.0905 |
| Verified tier-1 provider | \(\text{Beta}(9999, 1)\) | 0.9999 | \(1.0\times 10^{-4}\) |

### 2.2 Compute Tier (\(k\)-of-\(N\))

Each zone is healthy only if both its Lambda runner and its EC2 worker are (series):

\[
A_{\text{compute},z} = A_{\lambda,z}\cdot A_{\text{EC2},z} = 0.9995 \times 0.999 = 0.9985005
\]

The tier survives while at least 2 of 3 zones are healthy. With identical independent zones,

\[
A_{\text{compute}} = \sum_{j=2}^{3}\binom{3}{j} a^j (1-a)^{3-j} = 0.99999326
\]

Common-cause failure (a bad control-plane deploy hitting all zones) is added through \(\beta_{\text{CCF}}\) as in [02 §4.1](../02-risk-model.md); the figure above is the independent case.

### 2.3 Database Tier (Failover)

The tier is down if the primary fails and the failover does not succeed onto a healthy standby:

\[
A_{\text{DB}} = 1 - \left[(1 - A_{\text{Primary}})\big((1 - P_{\text{failover}}) + P_{\text{failover}}(1 - A_{\text{Standby}})\big)\right]
\]

With \(A_{\text{Primary}} = A_{\text{Standby}} = 0.999\) and \(P_{\text{failover}} = 0.95\):

\[
A_{\text{DB}} = 1 - 0.001\,(0.05 + 0.95 \times 0.001) = 0.99994905
\]

## 3. Series Result

\[
A_{\text{service}} = A_{\text{CDN}} \cdot A_{\text{compute}} \cdot A_{\text{DB}}
\]

The compute and database tiers contribute \(0.99999326 \times 0.99994905 = 0.99994231\) together. Because the structure is a product of independent factors, the expected value of the service availability is the product of the expected values.

## 4. Risk in Dollars

Take a 30-day horizon (720 hours) and a consequence of \$10,000 per hour of unavailability. The expected loss is \(E[\mathcal{R}] = (1 - E[A_{\text{service}}]) \times 720 \times 10{,}000\).

| CDN case | \(E[A_{\text{service}}]\) | Expected 30-day loss | 95th percentile of expected loss given the epistemic draw |
|----------|---------------------------|----------------------|------------------------------------------------------------|
| Unknown vendor, \(\text{Beta}(9,1)\) | 0.89995 | \$720,374 | \$2,038,825 |
| Verified tier-1, \(\text{Beta}(9999,1)\) | 0.99984 | \$1,135 | \$2,572 |

The 95th-percentile column uses the 5th percentile of the CDN availability, which for \(\text{Beta}(\alpha,1)\) is \(0.05^{1/\alpha}\) (the CDF is \(x^\alpha\)): 0.7169 for the unknown vendor and 0.99970 for the verified one. It shows the effect of epistemic uncertainty directly: the unknown vendor does not only have a lower mean, it has a long tail.

A point-SLA calculation that multiplies advertised figures (0.9999 for the CDN) gives \$1,135 regardless of whether that figure has been verified. The unknown-vendor prior here is a deliberately pessimistic modeling choice for illustration; the framework's contribution is that the choice is explicit, carries a distribution, and is reduced by evidence rather than by assertion.

## 5. Failure Modes in the Model

The EC2 worker Subassembly in the schema example includes three modes:

| Mode | Mechanism | Driving Element |
|------|-----------|-----------------|
| Memory leak (OOM risk) | `CapacitiveAccumulation` | `memory_pool` (Capacitance) |
| Connection starvation | `ResistiveThrottle` | `connection_path` (Resistance) |
| Thread-pool starvation | `InductiveMomentumCollapse` | `thread_pool` (Inductance) |

Their combination follows [03 §4](../03-failure-modes.md), and a rising hazard in one mode is attributed using [03 §5](../03-failure-modes.md).

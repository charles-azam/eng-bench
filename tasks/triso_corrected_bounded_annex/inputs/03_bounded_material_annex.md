# Corrected bounded material annex

This annex contains useful constitutive inputs but is not a complete particle-failure model. Section
6 lists material omissions that must be considered when assigning precision.

Use `R = 8.314 J/(mol K)` and absolute temperature in kelvin unless stated otherwise.

## 1. Elastic and irradiation inputs

| Property | PyC | SiC |
|---|---:|---:|
| Young modulus | 3.96e4 MPa | 3.70e5 MPa |
| Elastic Poisson ratio | 0.33 | 0.13 |
| Thermal expansion coefficient | 5.5e-6 K-1 | 4.90e-6 K-1 |

Treat the porous buffer stiffness as approximately zero and mechanically disconnected from the
kernel and IPyC. The PyC creep coefficient imposed for the analogous K3/P4 benchmark cases is
`4.93e-4 (MPa * 1e25 n/m2)^-1`, with creep Poisson ratio 0.4. Its application to K6 is another prior
extrapolation. The source designates the K3/P4 PyC swelling law as correlation (e), but the full
polynomial and the irradiation stress history are not supplied here. The bounded annex therefore
cannot close a mechanistic failure-stress calculation.

## 2. Strength statistics: mean is not scale

Table 9.14 imposes the following benchmark properties, based on German standard calculations, for
cases directly analogous to HFR-K3 and HFR-P4:

| Layer | Reported mean strength | Weibull modulus |
|---|---:|---:|
| SiC | 873 MPa | 8.02 |
| PyC | 200 MPa | 5.0 |

For a two-parameter Weibull distribution,

```text
survival(sigma) = exp(-(sigma / sigma_scale)^m)
mean_strength = sigma_scale * Gamma_function(1 + 1/m)
```

Therefore the SiC scale corresponding to the reported mean is
`873 / Gamma_function(1 + 1/8.02) = 926.892 MPa`. Use 873 MPa as the mean and approximately
926.9 MPa as the scale; do not substitute one for the other. The effective stressed-volume
normalization needed for a detailed weakest-link size correction is not supplied. The 926.892 MPa
value is the scale only for the standard two-parameter Weibull CDF written above. Codes such as
PANAMA may use an `ln(2)`-based or median parameterization; reconcile the exact convention before
inserting this scale into another formula.

HFR-K6 is not among Table 9.14's cases 9-13. Using the same strength distribution for K6 is an
explicit extrapolation across particle batches, not K6 characterization data; show its effect in the
Case B uncertainty analysis.

Provenance: IAEA TECDOC-1674 Table 9.14, report p. 520.

## 3. Corrected caesium diffusion through intact SiC

IAEA TECDOC-1674 Eq. 10.9 gives

```text
D_Cs_SiC = 5.5e-14 * exp(Gamma / 5) * exp(-125000 / (R*T))
         + 1.6e-2 * exp(-514000 / (R*T))                 [m2/s]
```

where Gamma is the reactor-specific fast fluence in units of `1e25 n/m2` above 16 fJ. Since
`16 fJ` is approximately `0.1 MeV`, use each case's supplied above-0.1-MeV fluence directly in this
equation: A1 3.9, A2 about 6.0 (5.9 in the heating-inventory table), B 4.8, C1 7.5, and C2 5.5.
Do not divide these values by 1.10 for Eq. 10.9; that conversion applies only to correlations stated
for the above-0.18-MeV convention.

The source's reference checksum uses `Gamma = 2`. With that value, the fluence factor applies inside
the first term as `exp(Gamma/5)` and does not multiply the second term. At 1600 C the equation gives
approximately `1.010e-16 m2/s`, matching the source's rounded `1.011e-16 m2/s`. Verify that checksum,
then use the case-specific values above for transport predictions.

Provenance: IAEA TECDOC-1674 Eq. 10.9, report p. 547; independently legible coefficient table in
IAEA TECDOC-2090 Table 88, report p. 219.

## 4. Reduced kernel diffusion and release after failure

Reduced diffusion coefficients `D_prime = D/r2` for a kernel treated as an equivalent sphere:

| Species | D0 prime (s-1) | Activation energy (kJ/mol) |
|---|---:|---:|
| Cs | 0.90 | 209 |
| Xe/Kr | 2.1e-5 | 126 |
| Stable/long-lived Xe/Kr alternative | 5e-3 | 155.4 |

For a bare or failed kernel held at constant temperature, cumulative fractional release is

```text
F = 1 - (6/pi2) * sum(n=1..infinity, exp(-n2*pi2*D_prime*t) / n2)
```

with approximations

```text
F = 6*sqrt(D_prime*t/pi) - 3*D_prime*t              when D_prime*t <= 0.15
F = 1 - (6/pi2)*exp(-pi2*D_prime*t)                 when D_prime*t > 0.15.
```

Apply piecewise integration or sufficiently small time steps for staged temperature histories. An
intact particle is controlled by transport through SiC and other layers; after an assumed through-
coating failure, the bare-kernel model is a conditional release model.

## 5. Inventory scaling

Absolute inventory scales approximately with burnup times heavy-metal loading. Fractional release is
normalized by each element's inventory. The mathematical population fraction for one particle is
`1 / particle_count`; this is useful as a normalization check but is not an observed detection event.

## 6. Explicit omissions and mechanism limits

The annex does not provide a unique quantitative model for:

- CO and fission-gas generation and internal pressure;
- the irradiation stress history needed to combine PyC shrinkage, creep, cracking, or debonding;
- kernel-coating mechanical interaction;
- palladium or other fission-product attack on SiC;
- as-manufactured defect distributions and correlations among layer dimensions;
- matrix sorption/transport and a complete intact multilayer release network;
- an effective-volume reference for weakest-link scaling.

The source identifies several possible failure mechanisms. It says rapid SiC thermal decomposition
occurs above 2000 C and is not expected to be a major contributor at normal or postulated accident
conditions for the cited designs. These cases peak at 1600-1800 C, so thermal decomposition cannot be
asserted as the unique missing mechanism without an explicit, labeled hypothesis.

Provenance: IAEA TECDOC-2090 Sections 7.5.4 and 7.5.4.3.

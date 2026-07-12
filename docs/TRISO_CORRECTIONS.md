# TRISO task-pack corrections and scope

This is a human audit record. It is not mounted into agent runs.

Canonical local source extractions:

- `triso/sources/TECDOC-1674_full.txt`, SHA-256
  `e902f1768d5f989f5d394207b170d5dc52aa0444998a03a15979bd4e59ef8de6`;
- `triso/sources/TECDOC-2090_full.txt`, SHA-256
  `d33534c8b035d9b0f25224d32cc8589f783a3c80647124b17cca97f22342b4f3`.

## Corrected Cs-in-SiC equation

IAEA TECDOC-1674 Eq. 10.9 (report p. 547) and IAEA TECDOC-2090 Table 88 (report p. 219) give:

```text
D = 5.5e-14 * exp(Gamma / 5) * exp(-125000 / (R*T))
  + 1.6e-2 * exp(-514000 / (R*T))                         [m^2/s]
```

with `Gamma = 2` in units of 10^25 n/m2 for the source's reference checksum and
`R = 8.314 J/(mol K)`. The former pack incorrectly
omitted `exp(Gamma/5)`, changed the second prefactor from `1.6e-2` to `1.6e-15`, and multiplied the
second term by fluence. The corrected expression gives `1.0097e-16 m2/s` at 1600 C, consistent with
the source's `1.011e-16 m2/s` after rounding.

The `Gamma = 2` value is not frozen for all task cases. Eq. 10.9 defines Gamma at `E > 16 fJ`,
which is approximately `E > 0.1 MeV`; therefore case transport uses the supplied reactor-specific
above-0.1-MeV fluence directly. The separate division by 1.10 applies only when a correlation calls
for the above-0.18-MeV convention.

## Weibull interpretation

TECDOC-1674 Table 9.14 (report p. 520) labels 873 MPa as the **SiC mean strength** and 8.02 as the
Weibull modulus for imposed benchmark properties based on German standard calculations. The values
are directly analogous to the K3/P4 cases; HFR-K6 is not among Table 9.14's cases 9-13. Their use for
K6 is therefore an explicit prior extrapolation, not a K6 strength measurement. For the standard
two-parameter Weibull convention

```text
mean = scale * Gamma_function(1 + 1/m),
```

the corresponding scale is

```text
873 / Gamma_function(1 + 1/8.02) = 926.892 MPa.
```

The task gives both the reported mean and the derived scale and does not treat them as interchangeable.
The 926.892 MPa value applies to the standard two-parameter Weibull CDF
`1 - exp(-(sigma/scale)^m)`; it is not automatically the input expected by a code using an
`ln(2)`-based, median, or effective-volume parameterization such as PANAMA.

## Bounded-annex interpretation

The annex is not represented as a complete mechanistic failure model. TECDOC-2090 Section 7.5.4
lists overpressure, PyC cracking/debonding/creep, matrix interactions, kernel migration, fission-product
attack, permeability, kernel-coating mechanical interaction, defects, and thermal decomposition as
possible contributors. Section 7.5.4.3 says rapid SiC thermal decomposition occurs above 2000 C and
is not expected to be important in normal operation or postulated accident conditions for the cited
designs. It is therefore not defensible to declare it the unique hidden mechanism for the 1600-1800 C
cases.

The corrected task asks for predictions but also requires the agent to identify which predictions are
not identifiable from the supplied pressure, corrosion, stress-history, and defect information.

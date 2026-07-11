# NSTF electrical-input curve provenance

This is a human audit record. It is **not included in the blind agent pack**.

## Source and omitted coefficient

The source is ANL-ART-47, *Final Project Report on RCCS Testing with the Air-Based NSTF*
(August 2016), local file
`rccs/sources/pdfs/NSTF_air_final_results_1350591.pdf`, SHA-256
`5737f481fa1c3052c9f8954880066305c86a98a1009f7d17283bdb8250e1e3e6`.

Relevant locations are Section 6.4.1, report pp. 152-155; Table 25, report p. 154; and Figure 69,
report p. 155 (PDF page 175).

The report defines

```text
P_electric_W = (C00 + C01*t_min + ... + C10*t_min^10) * Pscale
Pscale = 90  (estimated to yield 56 kWt)
```

but prints only `C00` through `C09`. Treating the missing `C10` as zero does not reproduce the
stated endpoint and soon becomes nonphysical. Rather than fabricate a post-peak curve, this benchmark
reconstructs the single omitted coefficient from the source's registered endpoint:

```text
t_peak = 84.85 h = 5091 min
P_electric(t_peak) = 90,000 W
C10 = (90000 / 90 - sum(i=0..9, Ci * 5091^i)) / 5091^10
    = 6.462156403603905e-36
```

The independently possible derivative-zero reconstruction gives `6.4850060e-36` and 90.024 kWe at
84.85 h, only 0.027% above the registered endpoint. The endpoint-constrained coefficient is used
because it preserves the explicitly stated power value.

## Registered table

The electric column is the corrected polynomial evaluated at 12 h intervals. The supplied-duty
column applies the report's structural mapping `56.07 / 90` to that electric curve. The report calls
the 90 kWe scale an estimate intended to yield 56 kWt; this is precisely the information withheld in
the blind variant and supplied in the ablation.

| Time (h) | Electric command (kWe) | Supplied-ablation duty (kWt) |
|---:|---:|---:|
| 0 | 41.987794 | 26.158395 |
| 12 | 51.759711 | 32.246300 |
| 24 | 63.516175 | 39.570577 |
| 36 | 73.311818 | 45.673262 |
| 48 | 80.762658 | 50.315136 |
| 60 | 85.972870 | 53.561098 |
| 72 | 88.997093 | 55.445189 |
| 84.85 | 90.000000 | 56.070000 |

Linear interpolation is the only registered interpolation. Extrapolation beyond 84.85 h is forbidden.
`protocol/validate_task_packs.sh` independently evaluates the reconstructed polynomial and checks both
CSV files against it.

## Experimental-scope correction

ANL-ART-47 Section 7.3.1, report pp. 183-184, says Run014 reached the peak condition and was then
concluded. It does not establish an observed post-peak cooldown. The old claim that the experiment
"turned over and cooled" is therefore unsupported by this run and is excluded from both the new task
and its scorer.

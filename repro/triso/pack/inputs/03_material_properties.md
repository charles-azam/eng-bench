# Inputs 03 — Material-property and correlation annex (offline)

Everything needed to run the cases without external references. Equation numbers refer to the
accident/normal-operation benchmark specification (TECDOC-1674). Fast fluences use the unit
**10²⁵ n/m², E > 0.18 MeV** unless a correlation states otherwise; to convert a fluence given for
E > 0.1 MeV to E > 0.18 MeV, divide by 1.10.

---

## 1. Elastic and thermal properties (Table 9.6)

| Property | PyC (IPyC & OPyC) | SiC |
|---|---|---|
| Young's modulus of elasticity | 3.96 × 10⁴ MPa | 3.70 × 10⁵ MPa |
| Poisson's ratio (elastic) | 0.33 | 0.13 |
| Poisson's ratio in creep | 0.5 | — |
| Coefficient of thermal expansion | 5.5 × 10⁻⁶ K⁻¹ (5.35 × 10⁻⁶ for the full-TRISO irradiation case) | 4.90 × 10⁻⁶ K⁻¹ |

**Buffer convention:** the buffer is mechanically disconnected — its stiffness is taken as
≈ 0 so it carries no load and does not mechanically interact with the kernel or the IPyC; its
irradiation-induced dimensional change is neglected (spec §, lines 21195–21197). It matters only
as void volume for gas/CO pressure.

---

## 2. PyC dimensional change (swelling) and creep

**PyC irradiation-induced swelling strain rate (Eq 9.22):** a polynomial in fast fluence
x (10²⁵ n/m², E > 0.18 MeV), applied separately to the radial and tangential directions:

    ġ = Σ_{i=0..5} A_i · x^i          (9.22)

**PyC creep coefficient (Eq 9.23):** a polynomial in temperature T (°C):

    K = Σ_{i=0..2} A_i · T^i           (9.23)

Coefficients A_i (Table 9.8). For the accident heating cases (HFR-P4, HFR-K3, HFR-K6) use the
swelling **correlation (e)** for PyC; correlation (d) supplies the temperature-dependent creep
coefficient.

| Correlation | A₀ | A₁ | A₂ | A₃ | A₄ | A₅ |
|---|---|---|---|---|---|---|
| (a) radial | −2.22642×10⁻² | 2.00861×10⁻² | −7.77024×10⁻³ | 1.36334×10⁻³ | — | — |
| (a) tangential | −1.91253×10⁻² | 2.63307×10⁻³ | 1.69251×10⁻³ | −3.53804×10⁻⁴ | — | — |
| (b) radial | −2.12522×10⁻² | 1.83715×10⁻² | −5.05553×10⁻³ | 7.27026×10⁻⁴ | — | — |
| (b) tangential | −1.79113×10⁻² | −3.42182×10⁻³ | 5.03465×10⁻³ | −8.88086×10⁻⁴ | — | — |
| (c) radial | −1.80613×10⁻² | 9.82884×10⁻³ | −2.25937×10⁻³ | 4.03266×10⁻⁴ | — | — |
| (c) tangential | −1.78392×10⁻² | 1.71315×10⁻³ | 2.32979×10⁻³ | −4.91648×10⁻⁴ | — | — |
| (d) creep coeff. | 4.386×10⁻⁴ | −9.70×10⁻⁷ | 8.0294×10⁻¹⁰ | — | — | — |
| (e) radial, x < 6.08 | −1.43234×10⁻¹ | 2.62692×10⁻¹ | −1.74247×10⁻¹ | 5.67549×10⁻² | −8.36313×10⁻³ | 4.52013×10⁻⁴ |
| (e) radial, x > 6.08 | 0.0954 (constant) | — | — | — | — | — |
| (e) tangential, x < 6.08 | −3.24737×10⁻² | 9.07826×10⁻³ | −2.10029×10⁻³ | 1.30457×10⁻⁴ | — | — |
| (e) tangential, x > 6.08 | −0.0249 (constant) | — | — | — | — | — |
| (f) radial | −2.13483×10⁻² | 1.64999×10⁻² | −3.80252×10⁻³ | 4.73765×10⁻⁴ | — | — |
| (f) tangential | −1.83549×10⁻² | −3.29740×10⁻³ | 5.47396×10⁻³ | −1.03249×10⁻³ | — | — |

**PyC creep coefficient (scalar value used for the irradiation cases):**
**4.93 × 10⁻⁴ (MPa·10²⁵ n/m², E > 0.18 MeV)⁻¹** with a creep Poisson's ratio of **0.4**
(Table 9.14 for the sphere/compact cases; the analytical-case value is 2.71 × 10⁻⁴ with
creep ν = 0.5).

---

## 3. Layer strengths and Weibull statistics (Table 9.14)

For the irradiated sphere/compact cases (HFR-K3, HFR-K6, HFR-P4-type LEU fuel):

| Layer | Mean strength | Weibull modulus m |
|---|---|---|
| SiC | 873 MPa | 8.02 |
| PyC | 200 MPa | 5.0 |

(For reference only, the high-burnup HEU NPR-1 fuel uses SiC 572 MPa, m = 6.0; PyC 218 MPa,
m = 9.5.) Weibull strength is a characteristic (scale) strength; the probability that a given
particle's SiC survives a peak tangential stress σ scales as exp[−(σ/σ₀)^m] over the stressed
volume — i.e. failure probability rises steeply once σ approaches σ₀.

---

## 4. Kernel diffusion coefficients (Table 7.1)

Reduced Arrhenius diffusion coefficients of fission products **in the UO₂ kernel**,
D = D₀′ · exp(−Q/RT) (D₀′ in s⁻¹; this is already the *reduced* coefficient D/r² for the grain,
with the kernel treated as one equivalent sphere — see §6). R = 8.314 J/(mol·K), T in K.

| Species | D₀′ (s⁻¹) | Q (kJ/mol) |
|---|---|---|
| Caesium | 0.90 | 209 |
| Strontium | 3.5 × 10⁴ | 488 |
| Silver | 0.107 | 165 |
| Xenon / Krypton | 2.1 × 10⁻⁵ | 126 |
| Xenon / Krypton (for stable & long-lived gases) | 5 × 10⁻³ | 155.4 |

---

## 5. Caesium diffusion in the SiC layer (Eq 10.9)

The retention barrier for Cs is the intact SiC. Recommended Cs-in-SiC diffusion coefficient:

    D_Cs,SiC = 5.5×10⁻¹⁴ · exp(−125000 / R·T)  +  Γ · 1.6×10⁻¹⁵ · exp(−514000 / R·T)   [m²/s]  (10.9)

where R·T uses R = 8.314 J/(mol·K), T in K, and Γ is the fast fluence in 10²⁵ n/m² (E > 16 fJ),
taken = 2 for these cases. **Evaluated at 1600 °C this gives D_Cs,SiC ≈ 1.011 × 10⁻¹⁶ m²/s.**
(Note: one participant code inadvertently used a higher value, 1.477 × 10⁻¹⁶ m²/s, at 1600 °C —
either is "not in disagreement" with the recommendation; treat ~1 × 10⁻¹⁶ m²/s as the reference
1600 °C value and scale by the Arrhenius form for other temperatures.)

---

## 6. Fission-gas release from a bare/failed kernel — equivalent-sphere model (Eqs 10.7–10.8)

Once a particle's SiC has failed, the kernel behaves as a bare sphere and the cumulative
fractional release of a diffusing species is the classic equivalent-sphere solution:

    F = 1 − (6/π²) · Σ_{n=1..∞} (1/n²) · exp(−n²·π²·D′·t)          (10.7)

with the standard short/long-time approximations:

    F ≈ 6·√(D′·t/π) − 3·D′·t          for D′·t ≤ 0.15               (10.8a)
    F ≈ 1 − (6/π²)·exp(−π²·D′·t)       for D′·t > 0.15               (10.8b)

where D′ = D/r² is the reduced diffusion coefficient (s⁻¹), r the kernel radius, and t the
heating time (s). For an intact particle the SiC (§5) is the controlling barrier; for a failed
particle the kernel term (§4) controls.

---

## 7. In-reactor short-lived gas release — Booth / R/B model (Eqs 7.5–7.6)

Steady-state release-to-birth ratio for short-lived Xe/Kr from a kernel of reduced diffusion
coefficient D′ and decay constant λ (from solving ∇²c − (λ/D)c + p/D = 0 in a sphere):

    R/B = (3/μ)·[ (1/tanh μ) − 1/μ ],   with  μ = √(λ/D′)          (7.5–7.6)

Full transient and cumulative-release forms (Eqs 7.7–7.8) extend this with the exponential mode
sum. This model is primarily an in-pile / defective-fraction diagnostic; the heating-phase
release of a failed particle is governed by §6.

---

## 8. Fission-product inventory scaling and the detection threshold

- **Inventory scales with burnup.** The absolute amount of each fission product present in an
  element (and therefore the release *in becquerels*, before normalizing) is proportional to the
  number of fissions, i.e. to burnup (%FIMA) × heavy-metal loading. A *fractional* release is
  the released fraction of that inventory; a higher-burnup element that releases the same fraction
  releases more activity.
- **One-particle detection threshold (spheres):** the fission-gas (Kr-85) inventory of a single
  particle is ≈ 1/16,400 of the sphere's inventory, so **one failed particle in a sphere
  corresponds to a Kr-85 fractional release of ≈ 6 × 10⁻⁵.** A measured whole-element Kr-85
  fractional release below this level is consistent with zero heating-induced failures.
- **One-particle threshold (compacts):** because a compact holds far fewer particles (~1631), the
  fractional-release level corresponding to one failed particle is much higher,
  **≈ 6 × 10⁻⁴** for the HFR-P4 compacts.

These thresholds let you translate a predicted particle-failure count into an expected Kr-85
fractional release, and vice-versa.

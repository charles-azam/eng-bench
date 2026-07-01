# Calculation Note — RCCS blind scenarios B1, B2, B3

**Facility:** ½-axial-scale, air-cooled Reactor Cavity Cooling System (RCCS) test section
(19.03° / 12-riser sector of a 227-riser MHTGR design).
**Scope of this note:** the three additional operating scenarios in
`inputs/05_additional_scenarios.md` — **B1** partially blocked risers, **B2** heavy-gas (argon)
ingress, **B3** accident transient summer-vs-winter.
**Basis:** first-principles 1-D natural-circulation model built from `inputs/` only
(`output/rccs_model.py`, `output/scenarios.py`). No facility test data consulted. Cited
correlations are standard textbook results.

---

## 1. Method (one page)

The RCCS is a pump-less loop: an electrically heated steel plate (mock RPV) transfers heat across
an air cavity to a bank of 12 steel riser ducts, mostly by **thermal radiation** with a smaller
**cavity natural-convection** share. Heat conducts through the thin riser wall and is carried away
by air rising inside the risers; the buoyant air exits through an outlet plenum and chimney, and
cool air is drawn down a downcomer. With no pump, the loop mass flow is fixed by

> **buoyancy driving head = Σ friction losses (major + minor).**

I solve four coupled relations self-consistently for each operating point:

| # | Equation | Gives |
|---|---|---|
| 1 | Loop momentum: `g·[(ρ_in−ρ_m)·H_heat + (ρ_in−ρ_out)·H_above] = Σ (fL/D+K)·½ρV²` | mass flow ṁ |
| 2 | Air energy: `ΔT = Q_air/(ṁ·c_p)`, `T_out=T_in+ΔT` | riser ΔT, T_out |
| 3 | Riser wall: `T_wall = T_m + q″/h_i`, `h_i` from Nu(Re,Pr) | wall temperature |
| 4 | Plate energy: `Q_rad(T_p,T_wall) + Q_conv,cav(T_p,T_wall) = Q_air` | plate temperature, rad/conv split |

**Correlations used (cited):**
- Air properties: ideal-gas density; Sutherland viscosity & conductivity; `c_p(T)` fit
  (White, *Viscous Fluid Flow*; Incropera & DeWitt, *Fundamentals of Heat and Mass Transfer*, Table A.4).
- Duct friction: laminar `f=64/Re`; turbulent Haaland approximation to Colebrook.
- Internal forced convection: **Dittus–Boelter** `Nu=0.023 Re^0.8 Pr^0.4` (turbulent, heating;
  Incropera Eq. 8.60); Gnielinski in transition; `Nu=4.36` laminar.
- Plate→riser radiation: gray parallel-plate exchange
  `Q=Aσ(T_p⁴−T_w⁴)/(1/ε_p+1/ε_r−1)`.
- Cavity natural convection: **Churchill–Chu** vertical-plate correlation (Incropera Eq. 9.26).

**Key geometry (derived from `inputs/01`):** riser internal 0.2444 m × 0.0413 m → A=0.01008 m²,
D_h=0.0706 m; heated length 6.91 m; 12 risers; plate/cavity radiating area 10.18 m²;
buoyant heights H_heat=6.91 m, H_above=12.7 m (to 19.6 m discharge); single 24-in chimney
A=0.292 m² (B1) / dual 0.584 m² (B3).

**Assumptions & conventions (stated so they can be challenged):**
1. **Power convention.** The scaled *thermal duty* is taken as the heat actually removed by the
   air: **Q_air = 26.16 kW** (normal) and **56.07 kW** (peak). The larger electric power
   (~42 kWe / ~82 kWe) exceeds Q_air because of parasitic losses through the heater backing and
   the 6-in cavity insulation; those losses never reach the coolant and are excluded.
2. Riser surface emissivity is **not reported**; I use **ε_r = 0.80** (oxidized structural steel,
   Incropera Table A.11, range 0.7–0.85). Plate ε_p = 0.785 (measured).
3. Riser wall treated as ~isothermal at the section (steel k≈50 W/m·K spreads the front-face flux);
   reported `T_wall` is the section-mean at z=3500 mm — the **front (hot) face runs ~15–30 °C higher**.
4. Blocked ducts (B1) carry no flow and float hot, so they transmit ~zero *net* radiation; the
   effective radiative sink area is scaled by (open ducts)/12.
5. Inlet air temperature tracks the outdoor ambient (open loop).

**Baseline anchor (plausibility check, not a scenario):** at the Case-1 point (56 kWt, dual
chimney, T_in=20 °C) the model gives ṁ≈0.46 kg/s (28 kg/min), riser ΔT≈120 °C, plate≈351 °C,
radiative fraction≈0.81. These are physically sensible for a natural-circulation air RCCS at its
peak duty and give confidence in the relative predictions below.

---

## 2. Scenario B1 — Partially blocked riser ducts

**Configuration:** normal-operation load **Q_air = 26.16 kW**, natural circulation, **single
chimney stack open**, whole ducts blocked at their inlets in stages.

Blocking a duct removes both its flow area *and* its actively-cooled surface; the same total heat
must leave through fewer ducts. Flow falls, per-duct ΔT rises, and the plate must run hotter to
push the fixed heat into a smaller cooled sink.

**Predicted quantities (figure: `fig_B1_blockage.png`):**

| Stage | Ducts open | Blocked | ṁ (kg/s) | Δṁ vs ref | Riser ΔT (°C) | Riser wall T (°C) | Plate T (°C) | ΔT_plate | Rad. frac. |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 12 | 0 %   | 0.379 | —      | 68.6  | 94  | 236 | —      | 0.71 |
| 1 | 10 | 16.7 %| 0.333 | −12 %  | 78.1  | 105 | 260 | +24 °C | 0.73 |
| 2 | 8  | 33.3 %| 0.283 | −25 %  | 91.8  | 120 | 293 | +57 °C | 0.76 |
| 3 | 6  | 50 %  | 0.228 | −40 %  | 113.9 | 144 | 339 | **+104 °C** | 0.80 |

**Answers to the posed questions:**
- **When HALF the ducts are blocked, the plate temperature rises by ≈ +104 °C** (236 → ≈339 °C),
  riser ΔT nearly doubles (69 → 114 °C), and loop mass flow falls ≈ 40 %.
- **The degradation is graceful, not cliff-like — but mildly accelerating.** The per-stage plate-
  temperature increments grow (+24, +33, +47 °C), yet there is no abrupt threshold: no boiling, no
  flow reversal, no runaway. Two self-stabilising effects cushion the loss: (i) higher ΔT raises
  the buoyant driving head, so mass flow drops only 40 % when 50 % of the area is lost; (ii)
  radiation (∝T⁴) grows as the plate heats, so its share of heat removal rises from 0.71 to 0.80
  and helps clear heat into the remaining ducts.
- At 50 % blockage the plate (~339 °C) is still far below any steel integrity limit; the facility
  degrades safely.

**Confidence: MODERATE.** Trends and relative magnitudes are robust. The absolute plate rise
depends on assumption 4 (how much net radiation blocked ducts still transmit): if blocked ducts
transmit more than assumed, the +104 °C is an over-estimate. Emissivity 0.6↔0.8 shifts plate temp
by ≈15 °C; Q_air ±15 % shifts it ≈±20 °C.

---

## 3. Scenario B2 — Heavy-gas (argon) ingress

**Configuration:** steady natural circulation at ~42 kWe (Q_air≈26 kW); a large volume of **argon
(M=40)** suddenly enters the **inlet plenum at the bottom**, displacing air.

**Mechanism — a buoyancy (density) lock, then thermal self-recovery.**
Natural circulation runs only while the riser (hot-leg) gas is *lighter* than the downcomer
(cold-leg) gas. Argon is **1.38× denser than air at the same temperature** (40/29). When the dense
argon slug fills the riser bottoms:

- Density criterion: argon becomes buoyant against 20 °C inlet air only above
  **T = 293 K × (40/29) = 404 K = 131 °C** (figure `fig_B2_argon.png`). The pre-event riser mean
  gas was only ≈54 °C, far below this.
- Consequences: cold-argon-filled risers give a driving head of **−31 Pa** over the heated length
  (vs +37 Pa normally) — i.e. **net buoyancy reverses**. A cold-argon plug only **≈8 m tall
  cancels the entire ~37 Pa driving head**; the 6.9 m risers plus the plenum are more than enough.
  **→ Natural circulation stalls (and momentarily tends to reverse).**

**What the gas temperatures do.** With flow stalled, the ~26 kW keeps arriving but is no longer
convected away. The trapped riser gas heats rapidly (gas-only heat capacity: warming the ≈1.25 kg
of riser argon from 54 → 131 °C needs only ≈53 kJ ≈ 2 s of heating; realistically tens of seconds
to a couple of minutes once wall coupling and the plenum slug are included). Riser gas and wall
temperatures **spike by roughly +80 °C** (to the ~131 °C restart threshold and somewhat beyond),
and the plate temperature drifts up during the stall because its convective sink is temporarily
lost.

**Whether/when/how it recovers — self-recovery.** The heat source itself cures the fault: once the
riser argon is heated past ≈131 °C it becomes buoyant, flow re-establishes (now argon-driven), the
hot argon is expelled up the chimney, and fresh air is pulled down the downcomer, **purging the
argon**. A fully-argon loop would actually circulate *vigorously* (model: ṁ≈0.58 kg/s, ΔT≈87 °C —
argon's higher molar mass amplifies the density head), confirming argon per se is not the enemy;
the **cold dense slug at the loop bottom** is. As air replaces argon, the loop returns to its
original air state.

**Timescales (order-of-magnitude):**

| Phase | Estimate | Basis |
|---|---|---|
| Argon reaches risers / stall onset | seconds–tens of s | inlet-plenum flush ≈3 s at pre-event flow |
| Gas heats to buoyancy-neutral (restart) | ~0.5–3 min | 26 kW into trapped gas + partial wall coupling |
| Full purge / recovery to air | ~5–15 min | loop gas volume ≈19 m³, 2–5 turnovers at recovering flow |

**Net:** a **temporary stall (flow → ~0) with a self-limiting temperature excursion of order tens
of °C, followed by unaided recovery within minutes** — a genuine passive-safety feature, because
the very heat that must be removed is what restores the buoyant driving force.

**Confidence: LOW–MODERATE.** The density-lock criterion (131 °C, −31 Pa reversal) is firm
physics. The stall/recovery *timescales and peak overshoot* are order-of-magnitude only: a steady
1-D model cannot capture slug size, argon/air interface mixing, stratification, or possible flow
reversal dynamics. The most uncertain input is the **argon slug volume and mixing rate**, which set
how long the stall lasts and how high temperatures climb.

---

## 4. Scenario B3 — Accident transient: summer vs winter

**Configuration:** the Case-2 decay-heat transient (26 → 56 kW) run at winter ambient ≈10 °C and
summer ≈25 °C, dual chimney. The two endpoints requested — **initial normal load (26 kW)** and
**decay-heat peak (56 kW)** — are steady operating points, so they are solved directly. (Because
the transient is slow — peak at ~85 h — the system is quasi-steady throughout.)

**Predicted quantities (figure: `fig_B3_weather.png`):**

| Load | Quantity | Winter (10 °C) | Summer (25 °C) | Δ (winter→summer) | % |
|---|---|---|---|---|---|
| Normal 26 kW | mass flow | 0.396 kg/s | 0.375 kg/s | −0.021 | **−5.4 %** |
| | riser wall T | 81 °C | 100 °C | +18 °C | +22 % |
| | plate T | 228 °C | 239 °C | **+10 °C** | +4.5 % |
| | riser ΔT | 65.6 °C | 69.3 °C | +3.7 °C | +5.6 % |
| Peak 56 kW | mass flow | 0.481 kg/s | 0.454 kg/s | −0.026 | **−5.4 %** |
| | riser wall T | 138 °C | 158 °C | +21 °C | +15 % |
| | plate T | 345 °C | 354 °C | **+9 °C** | +2.7 % |
| | riser ΔT | 116 °C | 122 °C | +6.5 °C | +5.6 % |

**Answers to the posed questions:**
- **Most weather-sensitive: the riser duct wall / gas temperatures.** They rise ≈ +18–21 °C
  winter→summer — *more* than the 15 °C ambient change, because the warmer inlet also weakens the
  draft (ṁ down 5 %), which raises ΔT on top of the ambient offset. In fractional terms wall T
  moves 15–22 %.
- **Most protected: the heated-plate temperature.** It rises only **≈ +9–10 °C** for a +15 °C
  ambient swing. Reason: the plate temperature is set by *radiation*, which scales as T⁴ in
  **absolute** Kelvin; near 500–630 K a strong radiative coupling absorbs the extra load with only
  a small temperature increment, so the plate barely notices the weather.
- **Mass flow** changes modestly (−5.4 %): the buoyant driving head ∝ (ρ_cold−ρ_hot), and a 15 °C
  shift is a small fraction of the large hot-to-cold density difference.
- **Direction:** cold weather ⇒ denser inlet ⇒ stronger draft ⇒ higher ṁ ⇒ lower temperatures.
  Summer is the limiting (hotter) case for the accident; but even the summer peak plate temp
  (~354 °C) is well below steel limits.

**Does it level off or run away?** Level off. Both dominant heat-removal paths strengthen as the
plate heats — radiation as T⁴ and buoyant flow as √(driving head) — a strong negative feedback.
Each steady solution above *is* the leveled-off state; there is no runaway at 56 kW in either
season.

**Confidence: MODERATE–HIGH** for the *relative* (winter↔summer) changes — these are
differential and cancel most modeling error. Absolute temperatures carry ≈±25–40 °C uncertainty
(emissivity, parasitic-loss/Q_air convention). Most uncertain assumption: the **parasitic heat-loss
fraction (Q_air convention)**, which shifts all absolute temperatures together but barely affects
the winter↔summer deltas.

---

## 5. Summary of confidence & the single most uncertain assumption

| Scenario | Headline result | Confidence | Most uncertain assumption |
|---|---|---|---|
| B1 | Half-blocked ⇒ plate +≈104 °C, ṁ −40 %; graceful, mildly accelerating | Moderate | Net radiation still shed by hot blocked ducts (sink-area scaling) |
| B2 | Flow stalls (density lock, argon must reach 131 °C); self-recovers in minutes | Low–Moderate | Argon slug volume & argon/air mixing rate (set stall duration & overshoot) |
| B3 | Wall/gas T most weather-sensitive (+~20 °C); plate most protected (+~9 °C); ṁ −5 % | Moderate–High (relative) | Parasitic-loss fraction / Q_air convention (shifts absolutes, not deltas) |

**Overall most uncertain modeling choice across all three:** the **riser surface emissivity**
(unreported; assumed 0.80) together with the **parasitic-loss / power convention** — both move the
absolute plate and wall temperatures by ~15–40 °C but leave the qualitative conclusions and the
scenario-to-scenario *differences* intact.

*Files:* `rccs_model.py` (physics), `scenarios.py` (B1/B3 driver + printouts),
`make_plots.py` (figures), `fig_B1_blockage.png`, `fig_B2_argon.png`, `fig_B3_weather.png`.

#!/usr/bin/env python3
"""
TRISO accident-heating prediction model (offline, stdlib only).

Cases: A1 (HFR-K3/1), A2 (HFR-K3/3), B (HFR-K6/3), C1 (HFR-P4/3-7), C2 (HFR-P4/1-12).

Physics chain (correlations cited from inputs/03, TECDOC-1674 numbering):
  1. Fission inventory from burnup (FIMA x initial metal atoms).           [inputs 01, 03 s.8]
  2. Stable Xe+Kr released from kernel to buffer: Booth equivalent-sphere
     (Eqs 10.7/10.8) with the "stable & long-lived gases" kernel reduced
     diffusivity D' = 5e-3 exp(-155.4 kJ / RT) s^-1 (Table 7.1),
     integrated over the irradiation history and the furnace schedule.
  3. CO from free oxygen: Proksch-type estimate O/F = t_efpd^2 * 10^(-0.21-8500/T_K),
     capped at 0.15 O per fission (oxygen-balance argument).  NOT in the annex ->
     carried as an explicit assumption + sensitivity case.
  4. Internal pressure: ideal gas in buffer void (porosity of the 1.0 Mg/m3
     buffer vs 2.25 Mg/m3 theoretical, minus 10% for kernel swelling).
  5. SiC tangential stress: thin shell sigma = P r_mid / (2 t_eff).
     PyC shrinkage-induced compression on SiC (order -10..-50 MPa) neglected
     -> conservative (over-predicts failures).
  6. SiC high-temperature degradation, two channels:
     (a) thermal decomposition thinning, rate k = A exp(-514 kJ/RT); A anchored
         so the full 36 um layer is consumed in ~10 h at 2200 C (the accepted
         TRISO destruction temperature); 514 kJ/mol is the high-T activation
         energy the annex itself provides (Eq 10.9 second term).
     (b) Cs corrosion: penetration depth d = sqrt(int D_Cs,SiC dt); Weibull
         characteristic strength knocked down by factor (1 - KD*d/t_SiC),
         KD = 0.35 nominal (corroded SiC retains ~2/3 strength).
  7. Failure statistics: Pf = 1 - exp[-(sigma/sigma0_eff)^m], sigma0 = 873 MPa,
     m = 8.02 (Table 9.14); expected failures = N * max-to-date Pf.
  8. Kr-85 element release = failed particles x (vented buffer fraction +
     post-failure bare-kernel Booth release, Eq 10.8) + 1e-5 baseline
     (matrix uranium contamination / as-manufactured defects).
  9. Cs-137: transient spherical-shell diffusion through intact SiC
     (D_Cs,SiC of Eq 10.9, recalibrated so D(1600 C) = 1.011e-16 m2/s as the
     annex states; the printed 1.6e-15 prefactor is dimensionally inconsistent
     with that quoted value - 1.6e-2 reproduces it), fed by kernel Booth
     release of Cs (D' = 0.90 exp(-209 kJ/RT), Table 7.1), reservoir = space
     inside SiC, no solubility partition (conservative-high), zero-sink outer
     boundary (no matrix holdup credit); + failed particles releasing 90%.
"""

import json
import math
import os

R = 8.314           # J/mol/K
NA = 6.022e23
M_UO2 = 0.270       # kg/mol
SIGMA0 = 873e6      # Pa, SiC Weibull characteristic strength (Table 9.14)
WEIB_M = 8.02       # SiC Weibull modulus (Table 9.14)
Y_GAS = 0.31        # stable Xe+Kr atoms per fission (chart of nuclides, thermal U-235/Pu-239)
BASELINE_KR = 1e-5  # matrix contamination / pre-existing-defect baseline
RHO_C_TH = 2250.0   # theoretical graphite density kg/m3

# ---- kernel reduced diffusivities, Table 7.1 (D' = D0' exp(-Q/RT), s^-1) ----
D0_GAS, Q_GAS = 5e-3, 155400.0     # stable & long-lived Xe/Kr
D0_CS,  Q_CS = 0.90, 209000.0      # Cs in UO2 kernel

# ---- Cs in SiC, Eq 10.9 (recalibrated prefactor, see docstring) ----
_D1873_TARGET = 1.011e-16
_term1_1873 = 5.5e-14 * math.exp(-125000.0 / (R * 1873.15))
_CAL2 = (_D1873_TARGET - _term1_1873) / (1.6e-2 * math.exp(-514000.0 / (R * 1873.15)))

def d_cs_sic(TK, mult=1.0):
    return mult * (5.5e-14 * math.exp(-125000.0 / (R * TK))
                   + _CAL2 * 1.6e-2 * math.exp(-514000.0 / (R * TK)))

# ---- SiC thermal decomposition thinning rate (anchored Arrhenius) ----
Q_DEC = 514000.0                                  # J/mol (annex high-T activation energy)
K_DEC0 = (36e-6 / (10 * 3600.0)) / math.exp(-Q_DEC / (R * 2473.15))   # m/s prefactor

def k_dec(TK, mult=1.0):
    return mult * K_DEC0 * math.exp(-Q_DEC / (R * TK))

def booth_F(theta):
    """Cumulative fractional release, equivalent sphere (Eqs 10.8a/b)."""
    if theta <= 0.0:
        return 0.0
    if theta <= 0.15:
        return 6.0 * math.sqrt(theta / math.pi) - 3.0 * theta
    return min(1.0, 1.0 - (6.0 / math.pi ** 2) * math.exp(-math.pi ** 2 * theta))

# ------------------------------------------------------------------ geometry
BATCHES = {
    # radii/thicknesses in m, densities kg/m3 (inputs 01, Table 10.2)
    "K3": dict(rk=248.5e-6, t_buf=94e-6, t_ipyc=41e-6, t_sic=36e-6,
               rho_k=10810.0, rho_buf=1000.0),
    "K6": dict(rk=254.0e-6, t_buf=102e-6, t_ipyc=39e-6, t_sic=36e-6,
               rho_k=10720.0, rho_buf=1020.0),
}

# ------------------------------------------------------------------ cases
# schedule rows: (set-point C, ramp h, hold h); staircase per inputs 02
CASES = {
    "A1": dict(batch="K3", N=16400, fima=0.077, T_irr_C=1118.0, t_irr_h=8616.0,
               efpd=359.0,
               schedule=[(300, 0.5, 0.5), (1050, 1.5, 5.5), (1250, 0.5, 16.5),
                         (1550, 6.5, 0), (300, 1, 0), (1600, 9, 500)],
               phase_of_interest="1600 C / 500 h hold"),
    "A2": dict(batch="K3", N=16400, fima=0.106, T_irr_C=841.5, t_irr_h=8616.0,
               efpd=359.0,
               schedule=[(300, 0.5, 0.5), (1050, 1.5, 5.5), (1250, 0.5, 13.5),
                         (1800, 12, 25.5), (300, 1, 0), (1050, 1.5, 19.5),
                         (1250, 0.5, 19), (1800, 12, 74.5)],
               phase_of_interest="1800 C, 100 h total in two segments"),
    "B":  dict(batch="K6", N=14580, fima=0.109, T_irr_C=1140.0, t_irr_h=15216.0,
               efpd=634.0,
               schedule=[(300, 0.5, 7), (1050, 2, 13.5), (1600, 11, 99),
                         (20, 17, 0), (1700, 5.5, 100), (20, 17, 0),
                         (1800, 2, 100), (20, 17, 0), (300, 7, 0),
                         (1800, 1, 300)],
               phase_of_interest="staged 1600/1700/1800 C, 1800 C x 400 h total"),
    "C1": dict(batch="K3", N=1631, fima=0.139, T_irr_C=1075.0, t_irr_h=8424.0,
               efpd=351.0,
               schedule=[(300, 0.5, 0.5), (1050, 1.5, 5.5), (1250, 0.5, 13.5),
                         (1600, 7.5, 304)],
               phase_of_interest="1600 C / 304 h hold"),
    "C2": dict(batch="K3", N=1631, fima=0.111, T_irr_C=940.0, t_irr_h=8424.0,
               efpd=351.0,
               schedule=[(300, 0.5, 0.5), (1050, 1.5, 5.5), (1250, 0.5, 13.5),
                         (1600, 7.5, 304)],
               phase_of_interest="1600 C / 304 h hold"),
}

# ------------------------------------------------------------------ helpers
def geometry(batch):
    g = BATCHES[batch]
    rk = g["rk"]
    r_buf = rk + g["t_buf"]
    r_ipyc = r_buf + g["t_ipyc"]
    b = r_ipyc                      # SiC inner radius
    L = g["t_sic"]
    r_mid = b + L / 2.0
    Vk = 4.0 / 3.0 * math.pi * rk ** 3
    V_buf = 4.0 / 3.0 * math.pi * (r_buf ** 3 - rk ** 3)
    porosity = 1.0 - g["rho_buf"] / RHO_C_TH
    V_void = porosity * V_buf * 0.90          # -10 % for kernel swelling
    V_res = 4.0 / 3.0 * math.pi * b ** 3      # Cs reservoir inside SiC
    atoms_U = Vk * g["rho_k"] / M_UO2 * NA
    return dict(b=b, L=L, r_mid=r_mid, V_void=V_void, V_res=V_res,
                atoms_U=atoms_U)

def co_per_fission(T_irr_K, efpd, cap):
    """Proksch-type free-oxygen estimate (NOT in annex; flagged assumption)."""
    return min(cap, efpd ** 2 * 10.0 ** (-0.21 - 8500.0 / T_irr_K))

def build_segments(schedule, T0=20.0):
    """(t0, t1, T0, T1) linear segments in seconds/C from staircase rows."""
    segs, t, Tprev = [], 0.0, T0
    for (T, ramp, hold) in schedule:
        if ramp > 0:
            segs.append((t, t + ramp * 3600.0, Tprev, float(T)))
            t += ramp * 3600.0
        if hold > 0:
            segs.append((t, t + hold * 3600.0, float(T), float(T)))
            t += hold * 3600.0
        Tprev = float(T)
    return segs

# ------------------------------------------------------------------ main model
def run_case(name, KD=0.35, co_on=True, co_cap=0.15, dec_mult=1.0,
             dcs_mult=1.0, dt=30.0, nx=61, verbose=False):
    c = CASES[name]
    g = geometry(c["batch"])
    N = c["N"]
    fissions = g["atoms_U"] * c["fima"]
    n_gas_tot = fissions * Y_GAS / NA                     # mol if fully released
    T_irr = c["T_irr_C"] + 273.15
    t_irr = c["t_irr_h"] * 3600.0

    OF = co_per_fission(T_irr, c["efpd"], co_cap) if co_on else 0.0
    n_co = fissions * OF / NA

    # ---------- irradiation phase: preload states ----------
    theta_gas = D0_GAS * math.exp(-Q_GAS / (R * T_irr)) / 1.0 * t_irr
    theta_cs_k = D0_CS * math.exp(-Q_CS / (R * T_irr)) * t_irr
    int_dcs = d_cs_sic(T_irr, dcs_mult) * t_irr           # for corrosion depth
    L_loss = k_dec(T_irr, dec_mult) * t_irr               # ~0 at irradiation T

    # PDE grid through SiC shell (normalised Cs inventory M0 = 1)
    L = g["L"]; b = g["b"]
    dx = L / (nx - 1)
    r = [b + i * dx for i in range(nx)]
    C = [0.0] * nx
    M_res = 0.0
    released_cs = 0.0
    Fk_prev = 0.0
    A_in = 4.0 * math.pi * (b + dx / 2.0) ** 2
    A_out = 4.0 * math.pi * (b + L - dx / 2.0) ** 2

    def pde_step(D, dtl):
        nonlocal C, M_res, released_cs, Fk_prev
        # feed reservoir from kernel
        Fk = booth_F(theta_cs_k)
        M_res += (Fk - Fk_prev)
        Fk_prev = Fk
        C[0] = max(M_res, 0.0) / g["V_res"]
        C[-1] = 0.0
        Cn = C[:]
        for i in range(1, nx - 1):
            rp = (r[i] + r[i + 1]) / 2.0
            rm = (r[i] + r[i - 1]) / 2.0
            Cn[i] = C[i] + dtl * D * (rp * rp * (C[i + 1] - C[i])
                                      - rm * rm * (C[i] - C[i - 1])) / (dx * dx * r[i] * r[i])
        J_in = D * A_in * (C[0] - C[1]) / dx          # into shell
        J_out = D * A_out * (C[nx - 2] - C[nx - 1]) / dx
        M_res -= J_in * dtl
        released_cs += J_out * dtl
        C = Cn

    # march the irradiation phase for the Cs PDE (coarse dt, stability-limited)
    D_irr = d_cs_sic(T_irr, dcs_mult)
    dt_irr = min(2e4, 0.3 * dx * dx / max(D_irr, 1e-24))
    tt = 0.0
    theta_cs_k = 0.0
    while tt < t_irr:
        step = min(dt_irr, t_irr - tt)
        theta_cs_k += D0_CS * math.exp(-Q_CS / (R * T_irr)) * step
        pde_step(D_irr, step)
        tt += step

    # ---------- furnace phase ----------
    segs = build_segments(c["schedule"])
    t_end = segs[-1][1]
    Pf_max = 0.0
    fail_events = []          # (dPf, theta_gas_at_fail)
    onset_t = None
    hist = []
    tt = 0.0
    for (t0, t1, Ta, Tb) in segs:
        tloc = t0
        while tloc < t1:
            step = min(dt, t1 - tloc)
            frac = 0.0 if t1 == t0 else ((tloc + step / 2.0) - t0) / (t1 - t0)
            TK = (Ta + (Tb - Ta) * frac) + 273.15
            # state integrals
            theta_gas += D0_GAS * math.exp(-Q_GAS / (R * TK)) * step
            theta_cs_k += D0_CS * math.exp(-Q_CS / (R * TK)) * step
            int_dcs += d_cs_sic(TK, dcs_mult) * step
            L_loss += k_dec(TK, dec_mult) * step
            # Cs PDE (substep if needed for stability)
            D = d_cs_sic(TK, dcs_mult)
            nsub = max(1, int(step / (0.3 * dx * dx / max(D, 1e-24))) + 1)
            for _ in range(nsub):
                pde_step(D, step / nsub)
            # pressure & stress
            F_buf = booth_F(theta_gas)
            n_mol = n_gas_tot * F_buf + n_co
            P = n_mol * R * TK / g["V_void"]
            L_eff = max(L - L_loss, 2e-6)
            sigma = P * g["r_mid"] / (2.0 * L_eff)
            phi = min(1.0, math.sqrt(max(int_dcs, 0.0)) / L)
            s0 = SIGMA0 * (1.0 - KD * phi)
            Pf = 1.0 - math.exp(-((sigma / s0) ** WEIB_M))
            if Pf > Pf_max:
                fail_events.append((Pf - Pf_max, theta_gas))
                Pf_max = Pf
                if onset_t is None and N * Pf_max >= 1.0:
                    onset_t = tloc + step
            tloc += step
            tt = tloc
        hist.append((t1 / 3600.0, Tb, N * Pf_max))

    # ---------- releases ----------
    theta_end = theta_gas
    kr_failed = 0.0
    for (dPf, th_f) in fail_events:
        F_buf_f = booth_F(th_f)
        post = booth_F(theta_end - th_f)
        kr_failed += dPf * (F_buf_f + (1.0 - F_buf_f) * post)
    f_fail = Pf_max
    kr85 = kr_failed + BASELINE_KR
    cs137 = released_cs * (1.0 - f_fail) + 0.90 * f_fail

    # summary numbers at end of last hot hold
    F_buf_end = booth_F(theta_end)
    TK_peak = max(Tb for (_, _, _, Tb) in segs) + 273.15
    P_peak = (n_gas_tot * F_buf_end + n_co) * R * TK_peak / g["V_void"]
    return dict(case=name, N=N, failures_expected=N * Pf_max,
                Pf=Pf_max, onset_h=(onset_t / 3600.0 if onset_t else None),
                kr85=kr85, cs137=cs137, cs_intact=released_cs,
                P_peak_MPa=P_peak / 1e6, F_gas_end=F_buf_end, OF=OF,
                L_eff_end_um=max(L - L_loss, 0.0) * 1e6,
                phi_end=min(1.0, math.sqrt(int_dcs) / L),
                sigma_end_MPa=P_peak * g["r_mid"] / (2.0 * max(L - L_loss, 2e-6)) / 1e6,
                hist=hist)


def main():
    out = {}
    print(f"Cs-SiC prefactor recalibration: second-term D0 = {_CAL2 * 1.6e-2:.3e} m2/s "
          f"(D(1600C) = {d_cs_sic(1873.15):.4g}, D(1700C) = {d_cs_sic(1973.15):.4g}, "
          f"D(1800C) = {d_cs_sic(2073.15):.4g} m2/s)")
    print(f"SiC decomposition rate: {k_dec(1873.15)*3.6e9:.4f} um/h @1600C, "
          f"{k_dec(2073.15)*3.6e9:.4f} um/h @1800C\n")

    header = (f"{'case':<4} {'P_peak':>7} {'F_gas':>6} {'O/F':>6} {'sigma':>7} "
              f"{'L_eff':>6} {'phi':>5} {'E[fail]':>9} {'onset_h':>8} "
              f"{'Kr85':>9} {'Cs137':>9} {'Cs_intact':>9}")
    print(header)
    for name in ["A1", "A2", "B", "C1", "C2"]:
        rres = run_case(name)
        out[name] = rres
        onset_s = "-" if rres["onset_h"] is None else "%.0f" % rres["onset_h"]
        print(f"{name:<4} {rres['P_peak_MPa']:>7.1f} {rres['F_gas_end']:>6.3f} "
              f"{rres['OF']:>6.4f} {rres['sigma_end_MPa']:>7.0f} "
              f"{rres['L_eff_end_um']:>6.1f} {rres['phi_end']:>5.2f} "
              f"{rres['failures_expected']:>9.3f} {onset_s:>8} "
              f"{rres['kr85']:>9.2e} {rres['cs137']:>9.2e} {rres['cs_intact']:>9.2e}")

    # ---------------- sensitivity envelope ----------------
    print("\nSensitivity envelope (expected failures):")
    variants = {
        "nominal": dict(),
        "KD=0.20": dict(KD=0.20),
        "KD=0.50": dict(KD=0.50),
        "no CO": dict(co_on=False),
        "dec x3": dict(dec_mult=3.0),
        "dec /3": dict(dec_mult=1 / 3.0),
        "Dcs x1.46 (participant)": dict(dcs_mult=1.46),
    }
    sens = {}
    for name in ["A1", "A2", "B", "C1", "C2"]:
        row = {}
        for vn, kw in variants.items():
            row[vn] = run_case(name, **kw)
        sens[name] = row
        vals_f = [row[v]["failures_expected"] for v in variants]
        vals_kr = [row[v]["kr85"] for v in variants]
        vals_cs = [row[v]["cs137"] for v in variants]
        print(f"  {name}: fail {min(vals_f):.3f}..{max(vals_f):.1f}  "
              f"Kr {min(vals_kr):.1e}..{max(vals_kr):.1e}  "
              f"Cs {min(vals_cs):.1e}..{max(vals_cs):.1e}")
        for vn in variants:
            rr = sens[name][vn]
            ons = "-" if rr["onset_h"] is None else "%.0fh" % rr["onset_h"]
            print(f"      {vn:<26} fail={rr['failures_expected']:9.3f} "
                  f"onset={ons:>6} Kr={rr['kr85']:.2e} Cs={rr['cs137']:.2e}")

    # ---------------- write results.json ----------------
    onset_text = {
        "A1": "none (no failures predicted at any point of the 1600 C / 500 h hold)",
        "A2": "if any (E[n]=0.28, P(>=1)~24%): in the second 1800 C segment, i.e. after "
              "~60-100 h cumulative at 1800 C",
        "B": "first failure expected near the end of the 1700 C / 100 h hold; ~15 expected "
             "by the end of the first 1800 C / 100 h phase; ~95% of all failures occur "
             "during the final 1800 C / 300 h phase",
        "C1": "none expected (E[n]=0.04; if one occurs, late in the 1600 C / 304 h hold)",
        "C2": "none (no failures predicted during the 1600 C / 304 h hold)",
    }
    fail_text = {
        "A1": "0 of 16,400 (expected value 0.01)",
        "A2": "0-1 of 16,400 (expected value 0.3; P(>=1) ~ 24%)",
        "B": "~300 of 14,580 (central 283; credible band ~25-2000)",
        "C1": "0 of 1631 (expected value 0.04; P(>=1) ~ 4%)",
        "C2": "0 of 1631 (expected value 0.003)",
    }
    confidence = {
        "A1": dict(failures="high", onset="high",
                   kr85="high (quote as < 6e-5, the one-particle threshold; expect ~1e-5)",
                   cs137="low-medium (order of magnitude; model is conservative-high: "
                         "no Cs solubility partition at the SiC and no matrix holdup)"),
        "A2": dict(failures="medium-low", onset="medium",
                   kr85="medium (<= 1e-4)", cs137="medium (0.05-0.2)"),
        "B": dict(failures="low (order of magnitude only)", onset="medium",
                  kr85="low (1e-3 to 1.5e-1)", cs137="medium (0.3-0.7)"),
        "C1": dict(failures="medium-high", onset="high",
                   kr85="high (quote as < 6e-4, the compact one-particle threshold)",
                   cs137="low-medium (order of magnitude, conservative-high)"),
        "C2": dict(failures="high", onset="high",
                   kr85="high (< 6e-4)", cs137="low-medium (order of magnitude, "
                   "conservative-high)"),
    }

    def sig3(x):
        return float(f"{x:.3g}")

    results = {}
    for name in ["A1", "A2", "B", "C1", "C2"]:
        rres = out[name]
        row = sens[name]
        fails = rres["failures_expected"]
        results[name] = {
            "failures": fail_text[name],
            "failures_expected_value": sig3(fails),
            "failures_range_sensitivity": [sig3(min(row[v]["failures_expected"] for v in row)),
                                           sig3(max(row[v]["failures_expected"] for v in row))],
            "onset": onset_text[name],
            "kr85_release": sig3(rres["kr85"]),
            "kr85_range": [sig3(min(row[v]["kr85"] for v in row)),
                           sig3(max(row[v]["kr85"] for v in row))],
            "cs137_release": sig3(rres["cs137"]),
            "cs137_range": [sig3(min(row[v]["cs137"] for v in row)),
                            sig3(max(row[v]["cs137"] for v in row))],
            "confidence": confidence[name],
        }
    results["ranking"] = (
        "B > A2 > C1 > A1 > C2. Temperature dominates: the SiC degradation kinetics "
        "(Q ~ 514 kJ/mol) make 1800 C ~20x more damaging per hour than 1600 C, so the two "
        "1800 C cases (B with 400 h, A2 with 100 h) suffer most. Burnup is the second-order "
        "driver through internal pressure and inventory: it puts C1 (13.9 %FIMA) above the "
        "other 1600 C cases, and B's high burnup + longest hot time makes it worst overall."
    )
    results["most_uncertain"] = (
        "The high-temperature SiC degradation kinetics: the thermal-decomposition thinning "
        "rate (anchored only by the ~2200 C destruction temperature, activation energy 514 "
        "kJ/mol taken from the annex's Cs-in-SiC high-T term) and the strength knock-down from "
        "Cs corrosion (35% at full penetration, assumed). Combined with the steep Weibull "
        "modulus (m = 8.02) this makes the absolute 1800 C failure counts uncertain by about "
        "an order of magnitude, though the ranking and the ~zero-failure outcome at 1600 C "
        "are robust."
    )
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
TRISO accident-heating prediction model (offline).

Implements, from inputs/03_material_properties.md only:
  * pressure-vessel failure:   ideal-gas pressure in buffer void -> thin-shell SiC
    tangential stress -> Weibull failure probability (Table 9.14),
    phase-resolved over each furnace schedule;
  * Cs-137 release (intact particles): 1-D spherical finite-difference diffusion
    through the SiC shell, D_Cs,SiC anchored to Eq 10.9 (1.011e-16 m2/s @ 1600 C,
    Q = 125 kJ/mol Arrhenius scaling), kernel source from Table 7.1, including the
    irradiation-phase preload of the SiC;
  * Kr-85 release: zero through intact SiC; failed particles release per the
    equivalent-sphere kernel model (Eqs 10.7-10.8) with the stable-gas kernel
    coefficient (Table 7.1: D0'=5e-3 1/s, Q=155.4 kJ/mol).

Units SI unless noted. Temperatures in the schedule tables are deg C.
"""
import numpy as np

R = 8.314          # J/mol K
NA = 6.022e23
M_UO2 = 0.270      # kg/mol
RHO_PYC_TH = 2.25e3  # theoretical pyrocarbon density kg/m3 (for buffer porosity)
Y_GAS = 0.30       # stable+long-lived Xe+Kr atoms per fission (physics assumption)
O_PER_F = 0.05     # net free oxygen atoms per fission -> CO (assumption, 0.01-0.1)
SIG0 = 873.0e6     # SiC Weibull characteristic strength, Pa (Table 9.14)
M_WEIB = 8.02      # SiC Weibull modulus (Table 9.14)

# ---- kernel (reduced) diffusion coefficients, Table 7.1: D' = D0' exp(-Q/RT) [1/s]
def Dk_Cs(TK):  return 0.90   * np.exp(-209000.0 / (R * TK))
def Dk_gas(TK): return 5.0e-3 * np.exp(-155400.0 / (R * TK))

# ---- Cs in SiC (Eq 10.9). The annex instructs: take 1.011e-16 m2/s as the
# reference value at 1600 C and scale with the Arrhenius form (Q = 125 kJ/mol).
D_REF, T_REF, Q_SIC = 1.011e-16, 1873.15, 125000.0
def D_SiC(TK): return D_REF * np.exp(-(Q_SIC / R) * (1.0 / TK - 1.0 / T_REF))

def booth_F(tau):
    """Cumulative fractional release, equivalent sphere, Eqs 10.7/10.8. tau = D'*t."""
    if tau <= 0: return 0.0
    if tau <= 0.15:
        return min(1.0, 6.0 * np.sqrt(tau / np.pi) - 3.0 * tau)
    return 1.0 - (6.0 / np.pi**2) * np.exp(-np.pi**2 * tau)

# ---------------- particle batches ----------------
BATCH = {
    "EUO2308": dict(r_k=248.5e-6, t_buf=94e-6, t_ipyc=41e-6, t_sic=36e-6,
                    rho_k=10.81e3, rho_buf=1.00e3),
    "EUO2358": dict(r_k=254.0e-6, t_buf=102e-6, t_ipyc=39e-6, t_sic=36e-6,
                    rho_k=10.72e3, rho_buf=1.02e3),
}

def geometry(b):
    g = dict(BATCH[b])
    g["r_buf"] = g["r_k"] + g["t_buf"]
    g["r_sic_in"] = g["r_buf"] + g["t_ipyc"]
    g["r_sic_out"] = g["r_sic_in"] + g["t_sic"]
    g["r_sic_m"] = 0.5 * (g["r_sic_in"] + g["r_sic_out"])
    g["V_k"] = 4/3 * np.pi * g["r_k"]**3
    g["V_buf"] = 4/3 * np.pi * (g["r_buf"]**3 - g["r_k"]**3)
    g["V_void"] = g["V_buf"] * (1.0 - g["rho_buf"] / RHO_PYC_TH)   # buffer porosity
    g["V_res"] = g["V_k"]   # Cs reservoir volume for inner BC (central assumption)
    g["N_U"] = g["rho_k"] * g["V_k"] / M_UO2 * NA                  # U atoms/particle
    return g

# ---------------- cases ----------------
# schedule rows: (set-point C, ramp h, hold h); start at 20 C.
CASES = {
 "A1": dict(batch="EUO2308", N=16400, bu=0.077, Tirr=1120.0, tirr_h=8616.0,
            sched=[(300,0.5,0.5),(1050,1.5,5.5),(1250,0.5,16.5),(1550,6.5,0),
                   (300,1,0),(1600,9,500)],
            peak="1600 C / 500 h hold"),
 "A2": dict(batch="EUO2308", N=16400, bu=0.102, Tirr=840.0, tirr_h=8616.0,
            sched=[(300,0.5,0.5),(1050,1.5,5.5),(1250,0.5,13.5),(1800,12,25.5),
                   (300,1,0),(1050,1.5,19.5),(1250,0.5,19),(1800,12,74.5)],
            peak="1800 C / 100 h (two holds)"),
 "B":  dict(batch="EUO2358", N=14580, bu=0.109, Tirr=1140.0, tirr_h=15216.0,
            sched=[(300,1,7),(1050,2,13.5),(1600,11,99),(20,17,0),(1700,5.5,100),
                   (20,17,0),(1800,2,100),(20,17,0),(300,7,0),(1800,1,300)],
            peak="staged 1600/1700/1800/1800 C, 100+100+100+300 h"),
 "C1": dict(batch="EUO2308", N=1631, bu=0.139, Tirr=1075.0, tirr_h=8424.0,
            sched=[(300,0.5,0.5),(1050,1.5,5.5),(1250,0.5,13.5),(1600,7.5,304)],
            peak="1600 C / 304 h hold"),
 "C2": dict(batch="EUO2308", N=1631, bu=0.111, Tirr=940.0, tirr_h=8424.0,
            sched=[(300,0.5,0.5),(1050,1.5,5.5),(1250,0.5,13.5),(1600,7.5,304)],
            peak="1600 C / 304 h hold"),
}

def profile(sched):
    """schedule -> list of (t_s, T_K) nodes, piecewise linear, starting 20 C."""
    t, T = 0.0, 20.0 + 273.15
    nodes = [(t, T)]
    for Tset, ramp, hold in sched:
        TK = Tset + 273.15
        t += ramp * 3600.0; nodes.append((t, TK))
        if hold > 0:
            t += hold * 3600.0; nodes.append((t, TK))
    return nodes

def run_case(name, c, o_per_f=O_PER_F, vres_factor=1.0, verbose=True):
    g = geometry(c["batch"])
    N_fiss = c["bu"] * g["N_U"]
    n_gas_tot = Y_GAS * N_fiss / NA          # mol stable Xe+Kr per particle (if fully released)
    n_co = o_per_f * N_fiss / NA             # mol CO per particle (assumed all in void)
    V_res = g["V_res"] * vres_factor

    # ---------- Cs FD grid over SiC shell ----------
    Ngrid = 60
    r = np.linspace(g["r_sic_in"], g["r_sic_out"], Ngrid + 1)
    dr = r[1] - r[0]
    C = np.zeros(Ngrid + 1)                  # Cs conc, units: (fraction of M0)/m3
    M_out = 0.0                              # fraction of Cs inventory released past OPyC
    M_out_irr = 0.0
    shell_w = 4 * np.pi * r**2 * dr          # trapezoid weights
    shell_w[0] *= 0.5; shell_w[-1] *= 0.5

    tau_k_cs = 0.0                           # integral D'_Cs dt  (kernel Cs)
    tau_k_g = 0.0                            # integral D'_gas dt (kernel gas)
    sig_max = 0.0
    events = []                              # (t_h, T_C, P_MPa, sigma_MPa, E_Nfail)

    # time base: irradiation phase (constant Tirr) then furnace profile
    t_irr = c["tirr_h"] * 3600.0
    TirrK = c["Tirr"] + 273.15
    furn = profile(c["sched"])
    t_furn_end = furn[-1][0]

    def T_of(t):
        if t <= t_irr: return TirrK
        tf = t - t_irr
        for (t0, T0), (t1, T1) in zip(furn[:-1], furn[1:]):
            if tf <= t1:
                return T0 + (T1 - T0) * (tf - t0) / max(t1 - t0, 1e-9)
        return furn[-1][1]

    t_end = t_irr + t_furn_end
    t = 0.0
    Fgas_hist = []
    node_times = [t_irr + tn for tn, _ in furn]
    next_node = 0
    while t < t_end:
        TK = T_of(t)
        D = D_SiC(TK)
        dt = min(0.35 * dr * dr / max(D, 1e-22), 2000.0 if t < t_irr else 300.0)
        dt = min(dt, t_end - t)
        # snap to schedule nodes so phase bookkeeping is exact
        if next_node < len(node_times) and t + dt > node_times[next_node] - 1e-6:
            dt = max(node_times[next_node] - t, 1.0)

        # kernel transformed times
        tau_k_cs += Dk_Cs(TK) * dt
        tau_k_g += Dk_gas(TK) * dt
        Fk_cs = booth_F(tau_k_cs)

        # inner BC: kernel-released Cs, minus what already sits in SiC or escaped
        M_sic = float(np.dot(shell_w, C))
        M_avail = max(Fk_cs - M_sic - M_out, 0.0)
        C[0] = M_avail / V_res
        # explicit FD step, spherical
        lap = np.zeros_like(C)
        lap[1:-1] = (C[2:] - 2 * C[1:-1] + C[:-2]) / dr**2 \
                    + (C[2:] - C[:-2]) / dr / r[1:-1]
        C[1:-1] += D * dt * lap[1:-1]
        J_out = -D * (C[-1] - C[-2]) / dr          # C[-1]=0 sink
        M_out += J_out * 4 * np.pi * g["r_sic_out"]**2 * dt
        if t < t_irr: M_out_irr = M_out

        # pressure & stress (furnace + irradiation alike)
        Fg = booth_F(tau_k_g)
        n = n_gas_tot * Fg + n_co
        P = n * R * TK / g["V_void"]
        sig = P * g["r_sic_m"] / (2 * BATCH[c["batch"]]["t_sic"])
        if sig > sig_max: sig_max = sig
        # log at schedule nodes
        if next_node < len(node_times) and abs(t + dt - node_times[next_node]) < 2.0:
            Pf = 1 - np.exp(-((sig_max / SIG0) ** M_WEIB))
            events.append(((t + dt - t_irr) / 3600.0, T_of(t + dt) - 273.15,
                           P / 1e6, sig_max / 1e6, c["N"] * Pf))
            next_node += 1
        t += dt
        Fgas_hist.append((t, Fg))

    Pf_end = 1 - np.exp(-((sig_max / SIG0) ** M_WEIB))
    EN = c["N"] * Pf_end

    # Kr-85: intact SiC releases none; failed particles release booth fraction of
    # kernel gas accumulated from the (probability-weighted) peak-hold onward.
    # Conservatively credit failed particles with full release of their gas (F~1
    # at 1800 C; >=0.95 at 1600 C over the holds) -> use 1.0.
    F_Kr = Pf_end * 1.0
    F_Cs_failed = Pf_end * 1.0
    F_Cs = M_out + F_Cs_failed

    res = dict(name=name, EN=EN, Pf=Pf_end, sig_max=sig_max / 1e6,
               F_Kr=F_Kr, F_Cs=F_Cs, F_Cs_intact=M_out, F_Cs_irr=M_out_irr,
               thr=1.0 / c["N"], events=events,
               P_peak=max(e[2] for e in events), Fk_cs_end=booth_F(tau_k_cs),
               Fg_end=booth_F(tau_k_g))
    if verbose:
        print(f"\n=== Case {name}  ({c['peak']}) ===")
        print(f"  fissions/particle = {N_fiss:.3e}; gas = {n_gas_tot*1e9:.2f} nmol; "
              f"CO = {n_co*1e9:.2f} nmol; V_void = {g['V_void']*1e12:.1f}e-12 m3")
        print(f"  kernel release at end: F_gas = {res['Fg_end']:.3f}, F_Cs = {res['Fk_cs_end']:.3f}")
        print(f"  peak P = {res['P_peak']:.1f} MPa;  peak SiC sigma_t = {res['sig_max']:.0f} MPa")
        print(f"  Weibull P_fail/particle = {Pf_end:.2e}  ->  E[N_fail] = {EN:.3f} of {c['N']}")
        print(f"  P(>=1 failure) = {1-np.exp(-EN):.3f}")
        print(f"  Kr-85 fractional release = {F_Kr:.2e}  (1-particle threshold {res['thr']:.1e})")
        print(f"  Cs-137 fractional release = {F_Cs:.3e} "
              f"(intact-particle diffusion {M_out:.3e}, of which crossed in-pile {M_out_irr:.3e})")
        print("  schedule-node log (t_h into furnace, T_C, P_MPa, sig_max_MPa, E[Nfail]):")
        for e in events:
            print(f"    t={e[0]:7.1f} h  T={e[1]:6.0f} C  P={e[2]:5.1f}  "
                  f"sig_max={e[3]:5.0f}  E[N]={e[4]:.4f}")
    return res

if __name__ == "__main__":
    print("TRISO accident-heating predictions (central model)")
    print(f"assumptions: Y(Xe+Kr)={Y_GAS}/fission, O/f={O_PER_F}, buffer porosity vs {RHO_PYC_TH/1e3} g/cc,")
    print("             V_res = kernel volume (Cs concentration continuity), Gamma=2 in Eq 10.9")
    results = {}
    for k, c in CASES.items():
        results[k] = run_case(k, c)

    print("\n\n================ SENSITIVITIES ================")
    for k in CASES:
        lo = run_case(k, CASES[k], o_per_f=0.01, verbose=False)
        hi = run_case(k, CASES[k], o_per_f=0.10, verbose=False)
        print(f"{k}: E[N_fail] O/f=0.01 -> {lo['EN']:.4f} | 0.05 -> {results[k]['EN']:.4f} "
              f"| 0.10 -> {hi['EN']:.4f}")
    print()
    for k in CASES:
        g = geometry(CASES[k]["batch"])
        fac = (g["V_k"] + g["V_buf"] + 4/3*np.pi*((g["r_sic_in"])**3 - g["r_buf"]**3)) / g["V_k"]
        alt = run_case(k, CASES[k], vres_factor=fac, verbose=False)
        print(f"{k}: F_Cs central {results[k]['F_Cs']:.3e} | V_res=kernel+buffer+IPyC "
              f"(x{fac:.2f}) -> {alt['F_Cs']:.3e}")

    print("\n================ SUMMARY ================")
    print(f"{'case':4} {'E[Nfail]':>9} {'P(>=1)':>8} {'F_Kr85':>9} {'thr(1p)':>8} "
          f"{'F_Cs137':>9}")
    for k, rr in results.items():
        print(f"{k:4} {rr['EN']:9.4f} {1-np.exp(-rr['EN']):8.3f} {rr['F_Kr']:9.2e} "
              f"{rr['thr']:8.1e} {rr['F_Cs']:9.3e}")

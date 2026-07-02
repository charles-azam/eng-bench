import math
from calc import *
from cases import CASES

def build_time_temp_profile(t_irr_C, t_irr_h, schedule):
    """Returns list of (T_celsius, duration_h) isothermal/ramp segments, irradiation first.
    Ramps are split into 20 sub-steps (linear T) for numerical integration accuracy."""
    segs = []
    T_irr_mean = sum(t_irr_C) / len(t_irr_C)
    segs.append((T_irr_mean, t_irr_h))
    T_prev = 20.0  # furnace starts from room T implicitly; first row given as 300C w/ no ramp time
    for (T_set, ramp_h, hold_h) in schedule:
        if ramp_h:
            n = 20
            dt = ramp_h / n
            for i in range(n):
                Tm = T_prev + (T_set - T_prev) * (i + 0.5) / n
                segs.append((Tm, dt))
        else:
            # no ramp info (first row): treat as an instantaneous jump, negligible duration
            pass
        if hold_h:
            n_hold = 40
            dt_h_sub = hold_h / n_hold
            for _ in range(n_hold):
                segs.append((T_set, dt_h_sub))
        T_prev = T_set
    return segs, T_irr_mean

def geom(batch):
    r_k = batch["d_kernel"] / 2
    r_b = r_k + batch["t_buffer"]
    r_i = r_b + batch["t_ipyc"]
    r_s = r_i + batch["t_sic"]
    r_o = r_s + batch["t_opyc"]
    r_sic_mean = (r_i + r_s) / 2
    porosity_buffer = 1 - batch["rho_buffer"] / batch["rho_ipyc"]
    v_buffer_shell = 4/3*math.pi*(r_b**3 - r_k**3)
    v_free = porosity_buffer * v_buffer_shell
    return dict(r_k=r_k, r_b=r_b, r_i=r_i, r_s=r_s, r_o=r_o, r_sic_mean=r_sic_mean,
                porosity_buffer=porosity_buffer, v_free=v_free)

def fission_inventory(case, batch):
    M_avg = batch["enrichment"] * 235 + (1 - batch["enrichment"]) * 238
    hm_g_per_particle = case["hm_g"] / case["n_particles"]
    n_HM_mol = hm_g_per_particle / M_avg
    n_HM_atoms = n_HM_mol * NA
    fissions = n_HM_atoms * case["burnup_fima"] / 100
    return fissions

def buildup_then_decay(prod_rate, lam, t_prod_s):
    """Atoms present at end of a constant-rate production period of duration t_prod_s,
    with concurrent decay (standard buildup equation)."""
    if lam * t_prod_s < 1e-8:
        return prod_rate * t_prod_s
    return (prod_rate / lam) * (1 - math.exp(-lam * t_prod_s))

def cumulative_Fo_kernel(segs, D0, Q):
    """Sum D'(T_i)*dt_i over all segments. D0 (Table 7.1) is ALREADY the reduced
    coefficient D/r^2 for the kernel equivalent sphere (per annex note) -- do not
    divide by r^2 again."""
    Fo = 0.0
    for T_C, dt_h in segs:
        T_K = T_C + K0
        Dp = D0 * math.exp(-Q / (R_GAS * T_K))
        Fo += Dp * dt_h * 3600
    return Fo

def run_case(name, case):
    batch = case["batch"]
    g = geom(batch)
    x_fluence = (case["fluence_e01"] / 1e25) / 1.10  # convert E>0.1MeV -> E>0.18MeV units, in 1e25 n/m^2

    segs, T_irr_mean = build_time_temp_profile(case["t_irr_C"], case["t_irr_h"], case["schedule"])
    irr_segs = segs[:1]
    furnace_segs = segs[1:]

    fissions = fission_inventory(case, batch)
    n_gas_total_atoms = fissions * Y_GAS_TOTAL
    n_kr85_atoms_0 = fissions * Y_KR85          # produced, before decay bookkeeping
    n_cs137_atoms_0 = fissions * Y_CS137

    # --- Kr-85 / Cs-137 inventory at start of furnace test, corrected for decay during irradiation
    t_irr_s = case["t_irr_h"] * 3600
    kr85_prod_rate = n_kr85_atoms_0 / t_irr_s
    cs137_prod_rate = n_cs137_atoms_0 / t_irr_s
    N_kr85_t0 = buildup_then_decay(kr85_prod_rate, LAMBDA_KR85, t_irr_s)
    N_cs137_t0 = buildup_then_decay(cs137_prod_rate, LAMBDA_CS137, t_irr_s)

    # --- Gas-release Fourier number (stable/long-lived Xe/Kr kernel coefficient), full history
    Fo_gas_irr = cumulative_Fo_kernel(irr_segs, D0_KR_LONG, Q_KR_LONG)
    Fo_gas_total = cumulative_Fo_kernel(segs, D0_KR_LONG, Q_KR_LONG)
    F_gas_irr = release_fraction(Fo_gas_irr)
    F_gas_total = release_fraction(Fo_gas_total)

    # --- Kr-85-specific kernel release fraction (same D' row; decay negligible over test length)
    Fo_kr85_total = Fo_gas_total  # same species/row
    F_kr85_release_if_failed = release_fraction(Fo_kr85_total)

    # --- Cs-137 kernel Fourier number (fast; kernel is not the barrier) & SiC-permeation bound
    Fo_cs_kernel_total = cumulative_Fo_kernel(segs, D0_CS, Q_CS)
    F_cs_kernel = release_fraction(Fo_cs_kernel_total)

    Fo_cs_sic_upperbound = 0.0
    for T_C, dt_h in furnace_segs:
        T_K = T_C + K0
        D = D_Cs_SiC(T_K)
        Dp = D / (batch["t_sic"]) ** 2
        Fo_cs_sic_upperbound += Dp * dt_h * 3600
    F_cs_intact_upperbound = release_fraction(Fo_cs_sic_upperbound)
    tau_sic_lag_h = (batch["t_sic"] ** 2) / (6 * D_Cs_SiC(case["peak_T"] + K0)) / 3600

    # =========================== STRESS MODEL over the furnace schedule ===========================
    # thermal-mismatch stress (instantaneous fn of T) & pressure stress (needs cumulative Fo up to t)
    t_cursor_s = 0.0
    Fo_gas_running = Fo_gas_irr
    peak_sigma_net = -1e9
    peak_time_h = 0.0
    peak_T_at_peak = None
    trace = []
    for T_C, dt_h in furnace_segs:
        T_K = T_C + K0
        Dp = D0_KR_LONG * math.exp(-Q_KR_LONG / (R_GAS * T_K))  # already reduced (D/r^2)
        Fo_gas_running += Dp * dt_h * 3600
        F_now = release_fraction(Fo_gas_running)
        n_released_mol = F_now * n_gas_total_atoms / NA
        P_Pa = n_released_mol * R_GAS * T_K / g["v_free"]
        P_MPa = P_Pa / 1e6
        sigma_p = P_MPa * g["r_sic_mean"] / (2 * batch["t_sic"])

        # Composite 3-layer (IPyC+SiC+OPyC) force-balance/compatibility thermal-mismatch stress
        # (elastic, no creep -- the furnace ramp is far too fast for irradiation creep, which
        # requires fluence, not time). Same derivation as the swelling preload below, without
        # the creep term: sigma_s = E_s*(E_i t_i + E_o t_o)*eps0 / (E_i t_i + E_s t_s + E_o t_o).
        eps0_th = (ALPHA_PYC - ALPHA_SIC) * (T_C - T_irr_mean)
        num_pyc = E_PYC * batch["t_ipyc"] + E_PYC * batch["t_opyc"]
        denom = num_pyc + E_SIC * batch["t_sic"]
        sigma_th = E_SIC * num_pyc * eps0_th / denom

        sigma_net = sigma_p + sigma_th  # PyC preload added outside (constant per case)
        t_cursor_s += dt_h * 3600
        trace.append((t_cursor_s / 3600, T_C, P_MPa, sigma_p, sigma_th))
        if sigma_net > peak_sigma_net:
            peak_sigma_net = sigma_net
            peak_time_h = t_cursor_s / 3600
            peak_T_at_peak = T_C

    # --- PyC/SiC creep-modulated preload stress (steady-state, from correlation e tangential slope)
    h = 0.02
    depsdx_tan = (poly(E_TAN_LOW, min(x_fluence + h, X_BREAK)) - poly(E_TAN_LOW, max(x_fluence - h, 0))) / (2*h) \
        if x_fluence <= X_BREAK else 0.0
    K_creep = poly([4.386e-4, -9.70e-7, 8.0294e-10], T_irr_mean)
    sigma_ipyc_on_sic = depsdx_tan * batch["t_ipyc"] / (K_creep * batch["t_sic"])
    sigma_opyc_on_sic = depsdx_tan * batch["t_opyc"] / (K_creep * batch["t_sic"])
    sigma_preload = sigma_ipyc_on_sic + sigma_opyc_on_sic  # negative = compressive

    sigma_net_final = max(peak_sigma_net + sigma_preload, 0.0)
    Pf = 1 - math.exp(-(sigma_net_final / SIGMA0_SIC) ** M_SIC) if sigma_net_final > 0 else 0.0
    N_failed = case["n_particles"] * Pf

    # Onset time: restrict to the FINAL hold at the case's designated peak temperature (the
    # "case of interest" per inputs/02_cases.md) to avoid locking onto a transient stress spike
    # during an earlier intermediate excursion in staged schedules (e.g. A1's 1550C dwell before
    # the drop-and-reheat to 1600C). Find the last contiguous run where T == peak_T, then find
    # the first point within it reaching 90% of ITS local (within-window) maximum.
    peak_T_target = case["peak_T"]
    final_window = []
    for (th, TC, PMPa, sp, sth) in trace:
        if abs(TC - peak_T_target) < 1.0:
            final_window.append((th, TC, sp, sth))
        elif final_window:
            final_window = []  # reset: only keep the LAST contiguous run
    window_peak = max(sp + sth for (_, _, sp, sth) in final_window) if final_window else peak_sigma_net
    onset_time_h, onset_T = None, None
    for (th, TC, sp, sth) in final_window:
        if (sp + sth) >= 0.9 * window_peak:
            onset_time_h, onset_T = th, TC
            break
    if onset_time_h is None:
        onset_time_h, onset_T = peak_time_h, peak_T_at_peak

    # --- intact-particle Cs-137 release through SiC: upper bound (sphere-release analogy, over-
    # estimates because it assumes uniformly-distributed source rather than one-face permeation)
    # and an illustrative small-Fo-suppressed best estimate (pre-breakthrough transient damping).
    Fo_sic = Fo_cs_sic_upperbound
    damping = math.exp(-1 / (4 * Fo_sic)) if Fo_sic > 1e-6 else 0.0
    F_cs_intact_best = F_cs_intact_upperbound * damping

    frac_failed = N_failed / case["n_particles"]
    kr85_release_total = frac_failed * F_kr85_release_if_failed
    cs137_release_total = frac_failed * F_cs_kernel + (1 - frac_failed) * F_cs_intact_best

    return dict(
        name=name, g=g, fissions=fissions, x_fluence=x_fluence,
        n_gas_total_atoms=n_gas_total_atoms, N_kr85_t0=N_kr85_t0, N_cs137_t0=N_cs137_t0,
        Fo_gas_irr=Fo_gas_irr, F_gas_irr=F_gas_irr, Fo_gas_total=Fo_gas_total, F_gas_total=F_gas_total,
        F_kr85_release_if_failed=F_kr85_release_if_failed,
        Fo_cs_kernel_total=Fo_cs_kernel_total, F_cs_kernel=F_cs_kernel,
        Fo_cs_sic_upperbound=Fo_cs_sic_upperbound, F_cs_intact_upperbound=F_cs_intact_upperbound,
        tau_sic_lag_h=tau_sic_lag_h,
        peak_sigma_net=peak_sigma_net, peak_time_h=peak_time_h, peak_T_at_peak=peak_T_at_peak,
        sigma_preload=sigma_preload, sigma_net_final=sigma_net_final, Pf=Pf, N_failed=N_failed,
        T_irr_mean=T_irr_mean, depsdx_tan=depsdx_tan, K_creep=K_creep,
        onset_time_h=onset_time_h, onset_T=onset_T,
        F_cs_intact_best=F_cs_intact_best, frac_failed=frac_failed,
        kr85_release_total=kr85_release_total, cs137_release_total=cs137_release_total,
        trace=trace,
    )

if __name__ == "__main__":
    results = {}
    for name, case in CASES.items():
        results[name] = run_case(name, case)

    for name, r in results.items():
        print(f"\n=== Case {name} ===")
        print(f"  fissions/particle = {r['fissions']:.3e}, x(E>0.18MeV) = {r['x_fluence']:.2f}e25")
        print(f"  free volume = {r['g']['v_free']*1e18:.1f} um^3, porosity={r['g']['porosity_buffer']:.3f}")
        print(f"  n_gas_total_atoms/particle = {r['n_gas_total_atoms']:.3e}")
        print(f"  N_kr85_t0 = {r['N_kr85_t0']:.3e}, N_cs137_t0 = {r['N_cs137_t0']:.3e}")
        print(f"  Fo_gas_irr={r['Fo_gas_irr']:.3f} F_gas_irr={r['F_gas_irr']:.4f}  Fo_gas_total={r['Fo_gas_total']:.3f} F_gas_total={r['F_gas_total']:.4f}")
        print(f"  F_kr85_release_if_failed = {r['F_kr85_release_if_failed']:.4f}")
        print(f"  Fo_cs_kernel_total={r['Fo_cs_kernel_total']:.3e} F_cs_kernel={r['F_cs_kernel']:.4f}")
        print(f"  Fo_cs_sic_upperbound={r['Fo_cs_sic_upperbound']:.4f}  F_cs_intact_upperbound={r['F_cs_intact_upperbound']:.5f}  tau_SiC_lag(peakT)={r['tau_sic_lag_h']:.1f} h")
        print(f"  peak sigma_p+th = {r['peak_sigma_net']:.2f} MPa at t={r['peak_time_h']:.1f} h, T={r['peak_T_at_peak']} C")
        print(f"  sigma_preload(PyC->SiC) = {r['sigma_preload']:.2f} MPa  (depsdx_tan={r['depsdx_tan']:.5f}, K_creep={r['K_creep']:.3e})")
        print(f"  sigma_net_final = {r['sigma_net_final']:.2f} MPa   Pf = {r['Pf']:.3e}   N_failed = {r['N_failed']:.4f}")
        print(f"  onset: t={r['onset_time_h']:.1f} h  T={r['onset_T']} C")
        print(f"  F_cs_intact_best(illustrative) = {r['F_cs_intact_best']:.3e}")
        print(f"  ==> Kr-85 element release = {r['kr85_release_total']:.3e}   Cs-137 element release = {r['cs137_release_total']:.3e}")

    print("\n\n=== RANKING by expected failed-particle count ===")
    for name, r in sorted(results.items(), key=lambda kv: -kv[1]['N_failed']):
        print(f"  {name}: N_failed={r['N_failed']:.3f}  (Pf={r['Pf']:.2e})  Kr85={r['kr85_release_total']:.2e}  Cs137={r['cs137_release_total']:.2e}")

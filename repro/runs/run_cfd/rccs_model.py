"""
RCCS 1-D natural-circulation + heat-transfer model.

Half-axial-scale air-cooled Reactor Cavity Cooling System (12-riser, 19.03 deg
sector). Everything built from first principles + cited correlations. No facility
test data used.

Structure
---------
Two coupled balances solved by fixed-point iteration:

  (A) MOMENTUM (sets mass flow m_dot):
      buoyancy draft  Delta_p_drive(m_dot)  ==  loop friction+form losses
      Delta_p_loss(m_dot).
      Draft = g * integral over loop height of (rho_ambient - rho_internal(z)) dz.

  (B) ENERGY / HEAT TRANSFER (sets temperatures given m_dot and heat duty Q):
      - air temperature rise  dT = Q / (m_dot cp)
      - radiation enclosure plate<->riser (reradiating adiabatic side/back walls)
      - cavity natural convection plate<->air<->riser (parallel, minority path)
      - riser internal forced/mixed convection wall->air (Gnielinski)
      -> heated-plate temperature, riser wall temperature, rad/convection split.

Correlations cited inline.
"""
import numpy as np
from scipy.optimize import brentq
import airprops as ap

SIGMA = 5.670374419e-8      # Stefan-Boltzmann W/m2-K4
G = 9.80665                 # m/s2

# ----------------------------------------------------------------------------
# GEOMETRY  (SI, converted from inputs/01_facility_geometry.md)
# ----------------------------------------------------------------------------
IN = 0.0254

# Riser duct (single), rectangular tube 10 x 2 in outer, wall 0.188 in
r_out_a, r_out_b = 10 * IN, 2 * IN
r_wall = 0.188 * IN
r_in_a = r_out_a - 2 * r_wall          # 9.624 in internal (wide)
r_in_b = r_out_b - 2 * r_wall          # 1.624 in internal (narrow)
A1 = r_in_a * r_in_b                    # single-duct internal flow area [m2]
P1 = 2 * (r_in_a + r_in_b)             # internal wetted perimeter [m]
Dh = 4 * A1 / P1                        # hydraulic diameter [m]
N_RISER = 12
A_FLOW = N_RISER * A1                    # total loop flow area through risers
L_RISER_TOTAL = 295 * IN               # 7.49 m
L_HEAT = 6.82                           # heated riser length [m] (scaling table)
L_CAV_INT = 272 * IN                    # 6.91 m of riser inside cavity

# Internal convective area of risers over heated length
A_INT = N_RISER * P1 * L_HEAT

# Riser outer face areas over heated length (per bank)
A_front = N_RISER * r_out_b * L_HEAT    # 2-in narrow faces toward plate
A_side = N_RISER * r_out_a * L_HEAT     # 10-in wide faces (one side)

# Heated plate (mock RPV)
H_PLATE = 6.7                           # m
W_CAV = 52 * IN                         # 1.32 m cavity width
A_PLATE = 8.84                          # m2 (6.7 x 1.32 envelope; as-built ~10.18)
CAV_DEPTH = 0.7066                      # plate face -> riser front face [m]
EPS_PLATE = 0.785                       # measured 0.78-0.79
EPS_RISER = 0.80                        # ASSUMED (oxidized structural steel; not reported)

# Loop hydraulic segments (area A, equiv length L, hyd dia D)
A_DC = np.pi / 4 * (24 * IN) ** 2       # downcomer 24-in dia
D_DC = 24 * IN
L_DC = 184.5 * IN
A_CH = 0.58                             # dual chimney total area (baseline)
D_CH = 24 * IN                          # each stack 24-in
L_CH_V = 826 * IN                       # vertical equiv length
L_CH_H = 470 * IN                       # horizontal equiv length
H_DISCHARGE = 19.6                      # chimney discharge height [m] (baseline)

# ----------------------------------------------------------------------------
# HYDRAULICS
# ----------------------------------------------------------------------------
def friction_factor(Re):
    """Darcy friction factor, smooth duct.
    Laminar f=64/Re (Re<2300); turbulent Petukhov (Incropera eq 8.21):
    f=(0.790 ln Re -1.64)^-2, valid 3000<Re<5e6. Blend in transition."""
    if Re < 1.0:
        return 64.0
    if Re < 2300:
        return 64.0 / Re
    ft = (0.790 * np.log(Re) - 1.64) ** -2
    if Re < 3000:
        fl = 64.0 / 2300
        x = (Re - 2300) / 700.0
        return fl + x * (ft - fl)
    return ft


# Minor-loss K coefficients (Idelchik / Crane TP-410 typical values), stated in note
K_DC_ENTRY = 0.5      # atmosphere -> downcomer entrance + flow conditioner (lumped ~1.0)
K_DC_COND = 1.0       # flow conditioner/screen
K_DC_ELBOW = 0.3      # 90 deg elbow
K_PLENUM_EXP1 = 1.0   # downcomer -> inlet plenum sudden expansion
K_RISER_IN = 0.5      # plenum -> riser contraction/entrance
K_RISER_OUT = 1.0     # riser -> outlet plenum sudden expansion
K_CH_IN = 0.5         # outlet plenum -> chimney contraction
K_CH_ELBOW = 0.3 * 2  # two elbows in chimney run
K_CH_EXIT = 1.0       # chimney discharge to atmosphere


def loop_pressure_loss(m_dot, T_in, T_mean, T_ch):
    """Sum friction + form losses around the loop [Pa]. Velocities/densities
    evaluated per segment at local temperature."""
    # Densities
    rho_dc = ap.rho(T_in)
    rho_r = ap.rho(T_mean)
    rho_ch = ap.rho(T_ch)
    mu_dc = ap.mu(T_in)
    mu_r = ap.mu(T_mean)
    mu_ch = ap.mu(T_ch)

    # Segment velocities
    V_dc = m_dot / (rho_dc * A_DC)
    V_r = m_dot / (rho_r * A_FLOW)
    V_ch = m_dot / (rho_ch * A_CH)

    dp = 0.0
    # Downcomer
    Re_dc = rho_dc * V_dc * D_DC / mu_dc
    f_dc = friction_factor(Re_dc)
    dp += (f_dc * L_DC / D_DC + K_DC_ENTRY + K_DC_COND + K_DC_ELBOW) * 0.5 * rho_dc * V_dc**2
    # Inlet plenum expansion (referenced to downcomer velocity)
    dp += K_PLENUM_EXP1 * 0.5 * rho_dc * V_dc**2
    # Risers (parallel bank): friction + entrance + exit at riser velocity
    Re_r = rho_r * V_r * Dh / mu_r
    f_r = friction_factor(Re_r)
    dp += (f_r * L_RISER_TOTAL / Dh + K_RISER_IN + K_RISER_OUT) * 0.5 * rho_r * V_r**2
    # Chimney: friction + elbows + exit at chimney velocity, + contraction from plenum
    Re_ch = rho_ch * V_ch * D_CH / mu_ch
    f_ch = friction_factor(Re_ch)
    dp += K_CH_IN * 0.5 * rho_r * V_r**2   # contraction near riser exit velocity scale
    dp += (f_ch * (L_CH_V + L_CH_H) / D_CH + K_CH_ELBOW + K_CH_EXIT) * 0.5 * rho_ch * V_ch**2
    return dp, dict(V_dc=V_dc, V_r=V_r, V_ch=V_ch, Re_r=Re_r, f_r=f_r)


def buoyancy_draft(T_in, T_out, T_ref_cold, T_ch_top):
    """Buoyant driving pressure [Pa] from the closed-loop momentum integral
    Delta_p = g * oint rho dz  =  g * integral_0^H (rho_cold - rho_hot(z)) dz.
    T_ref_cold is the OUTDOOR ambient density reference (the atmospheric column
    the hot stack competes against - standard natural-draft/chimney relation).
    The ascending internal (hot) leg follows:
      - z in [0, L_HEAT]: linear rise T_in -> T_out (heated risers)
      - z in [L_HEAT, H_DISCHARGE]: chimney, linear T_out -> T_ch_top (small loss)
    (Chimney draft Delta_p = g*H*(rho_out - rho_gas); e.g. ASHRAE Handbook -
     Fundamentals, stack effect.)
    """
    rho_ref = ap.rho(T_ref_cold)
    nseg = 400
    z = np.linspace(0, H_DISCHARGE, nseg)
    T = np.where(z <= L_HEAT,
                 T_in + (T_out - T_in) * (z / L_HEAT),
                 T_out + (T_ch_top - T_out) * (z - L_HEAT) / (H_DISCHARGE - L_HEAT))
    rho_int = ap.rho(T)
    integrand = rho_ref - rho_int
    dp = G * np.trapezoid(integrand, z)
    return dp


# ----------------------------------------------------------------------------
# HEAT TRANSFER
# ----------------------------------------------------------------------------
def h_internal(m_dot, T_mean, T_wall):
    """Riser internal convection coefficient [W/m2-K].
    Gnielinski correlation (Incropera eq 8.62), valid 3000<Re<5e6, 0.5<Pr<2000:
      Nu = (f/8)(Re-1000)Pr / (1 + 12.7 sqrt(f/8)(Pr^{2/3}-1)),  f=Petukhov.
    For Re<3000 fall back to laminar Nu=4.0 (const-flux-ish rectangular duct,
    Incropera Table 8.1 aspect ~6 -> Nu~5; use 4 as conservative)."""
    rho_m = ap.rho(T_mean)
    mu_m = ap.mu(T_mean)
    Pr_m = ap.Pr(T_mean)
    k_m = ap.k(T_mean)
    V = m_dot / (rho_m * A_FLOW)
    Re = rho_m * V * Dh / mu_m
    if Re < 3000:
        Nu = 5.0
    else:
        f = (0.790 * np.log(Re) - 1.64) ** -2
        Nu = (f / 8) * (Re - 1000) * Pr_m / (1 + 12.7 * np.sqrt(f / 8) * (Pr_m**(2/3) - 1))
    # Buoyancy-aided vertical heated duct enhances Nu; we keep pure forced (conservative)
    return Nu * k_m / Dh, Re, Nu, V


def h_cavity_nc(T_plate, T_cav, H=H_PLATE):
    """Natural convection coefficient on the vertical hot plate facing the cavity
    [W/m2-K]. Churchill-Chu (Incropera eq 9.26) for a vertical plate:
      Nu = {0.825 + 0.387 Ra^{1/6}/[1+(0.492/Pr)^{9/16}]^{8/27}}^2
    Properties at film temperature."""
    Tf = 0.5 * (T_plate + T_cav)
    beta = 1.0 / Tf
    nu = ap.nu(Tf)
    alpha = ap.alpha(Tf)
    Pr = ap.Pr(Tf)
    dT = max(T_plate - T_cav, 1e-3)
    Ra = G * beta * dT * H**3 / (nu * alpha)
    Nu = (0.825 + 0.387 * Ra**(1/6) / (1 + (0.492 / Pr)**(9/16))**(8/27))**2
    return Nu * ap.k(Tf) / H, Ra


def riser_circumferential(Qline, h_i, T_air, k_steel=50.0, t=r_wall,
                          f_front=0.45, f_side=0.50, f_rear=0.05):
    """Solve steady circumferential heat conduction around one riser tube wall at
    a fixed axial station (thin-wall fin equation, periodic):
        k t d2T/ds2 + q_out(s) - h_i (T - T_air) = 0
    Qline = total heat absorbed per unit axial length by one riser [W/m].
    Flux is allocated front/side/rear by view-factor reasoning (f_* fractions).
    Returns (T_front_avg, T_mean, s, T)."""
    # mean-wall perimeter geometry (outer face widths used for incident flux area)
    b_out, a_out = r_out_b, r_out_a
    P = 2 * (a_out + b_out)
    n = 400
    ds = P / n
    s = np.arange(n) * ds
    # face index along perimeter: front(0..b), side1(b..b+a), rear(b+a..2b+a), side2(...)
    q = np.zeros(n)
    for i in range(n):
        pos = s[i]
        if pos < b_out:
            q[i] = f_front * Qline / b_out
        elif pos < b_out + a_out:
            q[i] = f_side * 0.5 * Qline / a_out
        elif pos < 2 * b_out + a_out:
            q[i] = f_rear * Qline / b_out
        else:
            q[i] = f_side * 0.5 * Qline / a_out
    # Build periodic finite-difference system: kt (T[i-1]-2T[i]+T[i+1])/ds^2 + q - h(T-Ta)=0
    A = np.zeros((n, n))
    rhs = np.zeros(n)
    kt = k_steel * t
    for i in range(n):
        A[i, i] = -2 * kt / ds**2 - h_i
        A[i, (i - 1) % n] += kt / ds**2
        A[i, (i + 1) % n] += kt / ds**2
        rhs[i] = -q[i] - h_i * T_air
    T = np.linalg.solve(A, rhs)
    n_front = int(b_out / ds)
    T_front = T[:max(n_front, 1)].mean()
    return T_front, T.mean(), s, T


def radiation_plate_riser(T_plate, T_riser):
    """Net radiative exchange plate -> riser bank [W].
    Two-surface enclosure with reradiating (adiabatic) side/back walls. With the
    N/S/W walls adiabatic, in steady state essentially all radiation leaving the
    plate is delivered to the risers, so the effective view factor -> 1 and:
      Q = sigma A (T_p^4 - T_r^4) / (1/eps_p + 1/eps_r - 1).
    (Incropera eq 13.24 parallel-plate limit; A = plate area.)"""
    denom = 1 / EPS_PLATE + 1 / EPS_RISER - 1
    return SIGMA * A_PLATE * (T_plate**4 - T_riser**4) / denom


# ----------------------------------------------------------------------------
# COUPLED SOLVER
# ----------------------------------------------------------------------------
def solve_steady(Q_to_air, T_in_C=20.0, T_amb_C=2.0, chimney_loss_frac=0.10,
                 A_ch=A_CH, H_disch=H_DISCHARGE, verbose=False):
    """Solve the coupled loop for a given heat duty delivered to the air Q_to_air [W].
    Returns dict of results. T_in_C = riser inlet air temp; T_amb_C = ambient
    density reference (outdoor)."""
    global A_CH, H_DISCHARGE
    A_CH_sav, H_sav = A_CH, H_DISCHARGE
    A_CH, H_DISCHARGE = A_ch, H_disch

    T_in = T_in_C + 273.15
    T_amb = T_amb_C + 273.15

    # --- Momentum: find m_dot balancing draft and loss ---
    def residual(m_dot):
        cp_m = ap.cp(T_in + 20)     # provisional
        dT = Q_to_air / (m_dot * cp_m)
        T_out = T_in + dT
        T_mean = 0.5 * (T_in + T_out)
        cp_m = ap.cp(T_mean)
        dT = Q_to_air / (m_dot * cp_m)
        T_out = T_in + dT
        T_mean = 0.5 * (T_in + T_out)
        T_ch = T_out - chimney_loss_frac * dT           # chimney mean temp
        T_ch_top = T_out - 2 * chimney_loss_frac * dT   # discharge temp
        draft = buoyancy_draft(T_in, T_out, T_amb, T_ch_top)
        loss, _ = loop_pressure_loss(m_dot, T_in, T_mean, T_ch)
        return draft - loss

    m_lo, m_hi = 0.05, 20.0
    m_dot = brentq(residual, m_lo, m_hi, xtol=1e-4)

    cp_m = ap.cp(T_in + 20)
    dT = Q_to_air / (m_dot * cp_m)
    T_out = T_in + dT
    T_mean = 0.5 * (T_in + T_out)
    cp_m = ap.cp(T_mean)
    dT = Q_to_air / (m_dot * cp_m)
    T_out = T_in + dT
    T_mean = 0.5 * (T_in + T_out)
    T_ch = T_out - chimney_loss_frac * dT
    T_ch_top = T_out - 2 * chimney_loss_frac * dT
    draft = buoyancy_draft(T_in, T_out, T_amb, T_ch_top)
    loss, hyd = loop_pressure_loss(m_dot, T_in, T_mean, T_ch)

    # --- Heat transfer: temperatures given m_dot, Q ---
    # Internal convection coefficient (mean over heated length)
    T_rw_guess = T_mean + 60.0
    h_i, Re_i, Nu_i, V_i = h_internal(m_dot, T_mean, T_rw_guess)

    # Circumferential tube-wall temperatures (mean-length flux) and coupled
    # radiation. Iterate: front-face temp <-> plate temp <-> radiative split.
    # Mid-plane air temperature (linear profile) = T_mean by symmetry.
    T_air_mid = T_mean
    Qline_riser = Q_to_air / (N_RISER * L_HEAT)        # W per m axial per riser (total)
    T_rw_front = T_mean + 80.0
    for _ in range(40):
        # radiation + cavity convection split, using the FRONT-face temp the plate sees
        def plate_balance(T_p):
            T_cav = 0.5 * (T_p + T_rw_front)
            h_c, _ = h_cavity_nc(T_p, T_cav)
            Qr = radiation_plate_riser(T_p, T_rw_front)
            Qc = h_c * A_PLATE * (T_p - T_cav)
            return Qr + Qc - Q_to_air
        T_plate = brentq(plate_balance, T_rw_front + 1, T_rw_front + 2000)
        T_cav = 0.5 * (T_plate + T_rw_front)
        h_c, Ra_c = h_cavity_nc(T_plate, T_cav)
        Q_rad = radiation_plate_riser(T_plate, T_rw_front)
        Q_conv_cav = h_c * A_PLATE * (T_plate - T_cav)
        # circumferential conduction with allocated flux -> front & mean wall temps
        T_front_new, T_rw_mean, s_arr, T_arr = riser_circumferential(
            Qline_riser, h_i, T_air_mid)
        if abs(T_front_new - T_rw_front) < 1e-2:
            T_rw_front = T_front_new
            break
        T_rw_front = 0.5 * T_rw_front + 0.5 * T_front_new
    rad_frac = Q_rad / (Q_rad + Q_conv_cav)

    T_rw = T_rw_mean
    q_rad_plane = Q_rad / A_PLATE
    q_conv_int_mid = h_i * (T_rw_front - T_air_mid)
    T_rw_front_mid = T_rw_front

    A_CH, H_DISCHARGE = A_CH_sav, H_sav

    return dict(
        Q_to_air=Q_to_air, m_dot=m_dot, m_dot_kgmin=m_dot * 60,
        dT=dT, T_in_C=T_in_C, T_out_C=T_out - 273.15, T_mean_C=T_mean - 273.15,
        T_amb_C=T_amb_C,
        draft_Pa=draft, loss_Pa=loss,
        V_riser=hyd['V_r'], Re_riser=hyd['Re_r'], f_riser=hyd['f_r'],
        V_dc=hyd['V_dc'], V_ch=hyd['V_ch'],
        h_i=h_i, Re_i=Re_i, Nu_i=Nu_i,
        T_rw_mean_C=T_rw - 273.15,
        T_rw_front_mid_C=T_rw_front_mid - 273.15,
        T_plate_C=T_plate - 273.15, T_cav_C=T_cav - 273.15,
        h_cav=h_c, Ra_cav=Ra_c,
        Q_rad=Q_rad, Q_conv_cav=Q_conv_cav, rad_frac=rad_frac,
        q_rad_plane=q_rad_plane, q_conv_int_mid=q_conv_int_mid,
    )


def report(r, title):
    print(f"\n{'='*70}\n{title}\n{'='*70}")
    print(f"  Heat to air Q          : {r['Q_to_air']/1000:8.2f} kW")
    print(f"  Mass flow m_dot        : {r['m_dot']:8.4f} kg/s  ({r['m_dot_kgmin']:.1f} kg/min)")
    print(f"  Air temp rise dT       : {r['dT']:8.2f} K   (T_out={r['T_out_C']:.1f} C)")
    print(f"  Riser velocity         : {r['V_riser']:8.3f} m/s  Re={r['Re_riser']:.0f}  f={r['f_riser']:.4f}")
    print(f"  Draft / loss           : {r['draft_Pa']:8.3f} / {r['loss_Pa']:.3f} Pa")
    print(f"  Internal h / Nu / Re   : {r['h_i']:8.2f} W/m2K  Nu={r['Nu_i']:.1f} Re={r['Re_i']:.0f}")
    print(f"  Riser wall T (mean)    : {r['T_rw_mean_C']:8.1f} C")
    print(f"  Riser wall T (front,mid): {r['T_rw_front_mid_C']:7.1f} C")
    print(f"  HEATED PLATE T (front) : {r['T_plate_C']:8.1f} C")
    print(f"  Cavity air T           : {r['T_cav_C']:8.1f} C   h_cav={r['h_cav']:.2f}")
    print(f"  Q_rad / Q_conv(cav)    : {r['Q_rad']/1000:8.2f} / {r['Q_conv_cav']/1000:.2f} kW")
    print(f"  RADIATIVE FRACTION     : {r['rad_frac']*100:8.1f} %")


if __name__ == "__main__":
    # Case 1 baseline: electric 82 kWe, scaled peak duty ~56 kW to air (rest parasitic)
    r1 = solve_steady(Q_to_air=56.0e3, T_in_C=20.0, T_amb_C=2.0)
    report(r1, "CASE 1  Baseline steady state (Q_to_air = 56 kW)")

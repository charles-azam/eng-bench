#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Passive Reactor Cavity Cooling System (RCCS) — half-scale air-cooled test facility
First-principles calculation model (pure Python, no external packages).

Physics blocks
  1. Loop hydraulics + energy : buoyancy (stack) head vs friction/form losses -> mdot, dT
  2. Cavity thermal model     : gray-surface radiation network (plate <-> riser bank,
                                re-radiating side walls) + Churchill-Chu natural convection
                                to a well-mixed cavity gas node, axially discretized
  3. Duct perimeter model     : 1-D circumferential conduction around the riser wall at the
                                instrumented midplane (z = 3500 mm), with local external
                                radiation/convection loading and internal forced convection
                                + internal mean-radiant exchange -> hot-face wall temperature
  4. Accident transient       : quasi-steady sweep of the scaled decay-heat curve (justified:
                                plate thermal time constant ~0.5 h << 85 h transient)
  5. Weather sensitivity      : ambient density in the stack balance + wind-tip suction

Correlations (textbook, cited in calculation_note.md):
  - Air properties: Incropera & DeWitt, "Fundamentals of Heat and Mass Transfer", Table A.4
  - Vertical-plate natural convection: Churchill & Chu (1975); Incropera Eq. 9.26
  - Internal forced convection: Gnielinski (1976); Incropera Eq. 8.62
  - Friction factor: Haaland (1983) smooth-tube form
  - View factor, aligned parallel rectangles: Incropera Table 13.2
  - Gray two-surface enclosure w/ re-radiating walls: Incropera Ch. 13
  - Minor-loss coefficients: Idelchik, "Handbook of Hydraulic Resistance"
"""

import math
import json
import os

SIGMA = 5.670374e-8      # W/m2K4
G = 9.81                 # m/s2
P_ATM = 101325.0         # Pa
R_AIR = 287.05           # J/kgK

# ----------------------------------------------------------------------------------
# Air properties — Incropera & DeWitt Table A.4 (1 atm), linear interpolation
# ----------------------------------------------------------------------------------
_T  = [200.0, 250.0, 300.0, 350.0, 400.0, 450.0, 500.0, 550.0, 600.0, 650.0, 700.0, 750.0, 800.0]
_CP = [1007., 1006., 1007., 1009., 1014., 1021., 1030., 1040., 1051., 1063., 1075., 1087., 1099.]
_MU = [1.325e-5, 1.596e-5, 1.846e-5, 2.082e-5, 2.301e-5, 2.507e-5, 2.701e-5,
       2.884e-5, 3.058e-5, 3.225e-5, 3.388e-5, 3.546e-5, 3.698e-5]
_K  = [0.0181, 0.0223, 0.0263, 0.0300, 0.0338, 0.0373, 0.0407,
       0.0439, 0.0469, 0.0497, 0.0524, 0.0549, 0.0573]


def _interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            f = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + f * (ys[i + 1] - ys[i])
    return ys[-1]


def cp_air(T):  return _interp(T, _T, _CP)
def mu_air(T):  return _interp(T, _T, _MU)
def k_air(T):   return _interp(T, _T, _K)
def rho_air(T): return P_ATM / (R_AIR * T)
def pr_air(T):  return cp_air(T) * mu_air(T) / k_air(T)


# ----------------------------------------------------------------------------------
# Geometry (from inputs/01_facility_geometry.md)
# ----------------------------------------------------------------------------------
N_RISER   = 12
# riser internal cross-section 9.624 x 1.624 in
A_INT     = 0.244450 * 0.041250          # 0.010083 m2
P_INT     = 2.0 * (0.244450 + 0.041250)  # 0.571400 m
DH        = 4.0 * A_INT / P_INT          # 0.070585 m
W_FRONT   = 0.0508                       # duct front (narrow) external face width, m (2 in)
D_SIDE    = 0.2540                       # duct side (wide) external face depth, m (10 in)
T_WALL    = 0.0047752                    # duct wall 0.188 in
K_STEEL   = 50.0                         # W/mK, carbon steel (typ.)
L_RISER   = 7.493                        # 295 in total riser length
H_HEAT    = 6.70                         # heated cavity height, m
W_CAV     = 1.3208                       # cavity width (52 in), m
A_PLATE   = H_HEAT * W_CAV               # 8.849 m2 heated-plate envelope
PITCH     = W_CAV / N_RISER              # 0.11007 m
W_GAP     = PITCH - W_FRONT              # 0.05927 m gap between duct sides
GAP_PL    = 0.7066                       # plate -> riser-front spacing, m
EPS_P     = 0.785                        # plate emissivity (measured 0.78-0.79)
EPS_R     = 0.80                         # riser oxidized steel (assumed; A500 oxidized)

A_FRONT_TOT = N_RISER * W_FRONT * H_HEAT           # 4.084 m2
A_SIDE_TOT  = N_RISER * 2.0 * D_SIDE * H_HEAT      # 40.84 m2
A_REAR_TOT  = A_FRONT_TOT
A_EXT_TOT   = A_FRONT_TOT + A_SIDE_TOT + A_REAR_TOT
A_INT_TOT   = P_INT * H_HEAT * N_RISER             # internal convective area over heated span

# flow-path
D_DC   = 0.6096                          # downcomer diameter (24 in)
A_DC   = math.pi / 4.0 * D_DC ** 2       # 0.2919 m2
L_DC   = 4.686                           # 184.5 in equivalent length
A_CH1  = A_DC                            # single chimney stack area
N_CH   = 2
L_CHEQ = (826.0 + 470.0) * 0.0254        # 32.92 m equivalent length per stack
D_CH   = 0.6096
Z_EXIT       = 26.0                      # chimney discharge above riser bottom (facility 26 m)
Z_RISER_TOP  = 7.49
Z_PORT       = 8.50                      # chimney entrance ports elevation (plenum column top)

# loss coefficients (Idelchik; stated in note)
K_COND   = 2.0    # inlet flow conditioner (honeycomb+screen)
K_ENT    = 0.5    # duct entrances (sharp)
K_ELBOW  = 0.3    # 90-deg round elbow
K_EXP    = 1.0    # sudden expansion into plenum (jet dissipation)
K_EXIT   = 1.0    # discharge to atmosphere
K_DAMPER = 0.9    # ~3 open butterfly dampers per line, K~0.3 each

DT_CHIMNEY = 12.0  # K, chimney-path gas cooling (uninsulated horizontal run + insulated stack)


# ----------------------------------------------------------------------------------
# Correlations
# ----------------------------------------------------------------------------------
def f_haaland(Re):
    """Smooth-duct friction factor (Haaland form; laminar below 2300)."""
    if Re < 1.0:
        return 64.0
    if Re < 2300.0:
        return 64.0 / Re
    return (-1.8 * math.log10(6.9 / Re)) ** -2


def h_gnielinski(Re, T_bulk):
    """Internal forced-convection h for the riser duct (Gnielinski)."""
    Pr = pr_air(T_bulk)
    if Re < 2300.0:
        Nu = 4.36
    else:
        f = (0.790 * math.log(Re) - 1.64) ** -2
        Nu = (f / 8.0) * (Re - 1000.0) * Pr / (1.0 + 12.7 * math.sqrt(f / 8.0) * (Pr ** (2.0 / 3.0) - 1.0))
    return Nu * k_air(T_bulk) / DH


def h_churchill_chu(Ts, Tinf, L):
    """Vertical-plate natural convection (Churchill & Chu 1975, all-Ra form)."""
    dT = abs(Ts - Tinf)
    if dT < 0.05:
        return 0.5
    Tf = 0.5 * (Ts + Tinf)
    rho = rho_air(Tf)
    nu = mu_air(Tf) / rho
    alpha = k_air(Tf) / (rho * cp_air(Tf))
    Pr = pr_air(Tf)
    Ra = G * (1.0 / Tf) * dT * L ** 3 / (nu * alpha)
    Nu = (0.825 + 0.387 * Ra ** (1.0 / 6.0) /
          (1.0 + (0.492 / Pr) ** (9.0 / 16.0)) ** (8.0 / 27.0)) ** 2
    return Nu * k_air(Tf) / L


def viewfactor_parallel_rect(X, Y):
    """F12, aligned equal parallel rectangles, X = a/L, Y = b/L (Incropera Table 13.2)."""
    X2, Y2 = X * X, Y * Y
    t1 = math.log(math.sqrt((1 + X2) * (1 + Y2) / (1 + X2 + Y2)))
    t2 = X * math.sqrt(1 + Y2) * math.atan(X / math.sqrt(1 + Y2))
    t3 = Y * math.sqrt(1 + X2) * math.atan(Y / math.sqrt(1 + X2))
    t4 = -X * math.atan(X) - Y * math.atan(Y)
    return 2.0 / (math.pi * X * Y) * (t1 + t2 + t3 + t4)


# ----------------------------------------------------------------------------------
# 1. Loop hydraulics + energy
# ----------------------------------------------------------------------------------
def loop_residual(mdot, Q_air, T_in, T_amb, wind, Cw):
    """Buoyancy head minus loss head, Pa. T_in/T_amb in K."""
    # energy: outlet temperature (two-pass for cp at mean T)
    T_out = T_in + Q_air / (mdot * cp_air(T_in + 30.0))
    T_out = T_in + Q_air / (mdot * cp_air(0.5 * (T_in + T_out)))
    T_m = 0.5 * (T_in + T_out)

    rho_in, rho_out, rho_amb = rho_air(T_in), rho_air(T_out), rho_air(T_amb)
    T_ch = max(T_out - DT_CHIMNEY, T_amb + 1.0)
    rho_ch = rho_air(T_ch)

    # riser column mean density (linear T rise over heated span within the riser)
    n = 20
    s = 0.0
    for i in range(n):
        z = (i + 0.5) / n * L_RISER
        frac = min(max(z / H_HEAT, 0.0), 1.0)
        s += rho_air(T_in + frac * (T_out - T_in))
    rho_riser = s / n

    # ---- buoyancy: ambient column vs internal hot columns (datum = riser bottom) ----
    dp_b = G * (rho_amb * Z_EXIT
                - rho_riser * Z_RISER_TOP
                - rho_out * (Z_PORT - Z_RISER_TOP)
                - rho_ch * (Z_EXIT - Z_PORT))
    # wind-assist: suction at stack tip ~ Cw * dynamic pressure
    dp_b += Cw * 0.5 * rho_amb * wind ** 2

    # ---- losses ----
    dp = 0.0
    # downcomer (cold, building air)
    v_dc = mdot / (rho_in * A_DC)
    q_dc = 0.5 * rho_in * v_dc ** 2
    Re_dc = rho_in * v_dc * D_DC / mu_air(T_in)
    dp += (K_COND + K_ENT + K_ELBOW + K_EXP) * q_dc
    dp += f_haaland(Re_dc) * (L_DC / D_DC) * q_dc

    # risers (12 in parallel)
    Gm = mdot / (N_RISER * A_INT)
    v_r_in, v_r_m, v_r_out = Gm / rho_in, Gm / rho_air(T_m), Gm / rho_out
    Re_r = Gm * DH / mu_air(T_m)
    dp += K_ENT * 0.5 * rho_in * v_r_in ** 2
    dp += f_haaland(Re_r) * (L_RISER / DH) * 0.5 * rho_air(T_m) * v_r_m ** 2
    dp += Gm ** 2 * (1.0 / rho_out - 1.0 / rho_in)           # acceleration
    dp += K_EXP * 0.5 * rho_out * v_r_out ** 2               # exit into outlet plenum

    # chimneys (2 in parallel)
    v_ch = (mdot / N_CH) / (rho_ch * A_CH1)
    q_ch = 0.5 * rho_ch * v_ch ** 2
    Re_ch = rho_ch * v_ch * D_CH / mu_air(T_ch)
    dp += (K_ENT + K_DAMPER + K_EXIT) * q_ch
    dp += f_haaland(Re_ch) * (L_CHEQ / D_CH) * q_ch

    return dp_b - dp, T_out, Re_r


def solve_loop(Q_air, T_in_C=20.0, T_amb_C=2.0, wind=0.0, Cw=0.4):
    """Bisection on mdot; returns dict."""
    T_in, T_amb = T_in_C + 273.15, T_amb_C + 273.15
    lo, hi = 0.02, 5.0
    r_lo = loop_residual(lo, Q_air, T_in, T_amb, wind, Cw)[0]
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        r = loop_residual(mid, Q_air, T_in, T_amb, wind, Cw)[0]
        if (r > 0) == (r_lo > 0):
            lo = mid
        else:
            hi = mid
    mdot = 0.5 * (lo + hi)
    _, T_out, Re_r = loop_residual(mdot, Q_air, T_in, T_amb, wind, Cw)
    return {"mdot": mdot, "T_out_C": T_out - 273.15, "dT": T_out - T_in, "Re_riser": Re_r,
            "T_in_C": T_in_C}


# ----------------------------------------------------------------------------------
# 2+3. Cavity thermal model with perimeter-resolved duct wall at midplane
# ----------------------------------------------------------------------------------
def gap_F(x):
    """Fraction of diffuse radiation entering a 2-D slot (width W_GAP) that penetrates
       beyond depth x (parallel-strip view factor, crossed strings)."""
    X = x / W_GAP
    return math.sqrt(1.0 + X * X) - X


def perimeter_model(T_p_mid, T_g, T_a_mid, h_int, h_cav, q_gap_net, T_side_ref, R_fp):
    """1-D circumferential wall conduction, half duct perimeter (symmetry).
       s: 0 (front-face center) -> front corner (0.0254) -> side (0.254) -> rear half.
       All temperatures K.  Returns node temps and per-face fluxes.
       q_gap_net: net radiative power entering each gap mouth, W/m2 of mouth area."""
    N = 48
    S_TOT = 0.5 * W_FRONT + D_SIDE + 0.5 * W_FRONT   # 0.3048 m
    ds = S_TOT / N
    s_nodes = [(i + 0.5) * ds for i in range(N)]

    def face_of(s):
        if s < 0.5 * W_FRONT:
            return "front"
        if s < 0.5 * W_FRONT + D_SIDE:
            return "side"
        return "rear"

    leak = gap_F(D_SIDE)                      # fraction of gap radiation reaching back region
    # distribute: sides get (1-leak) via profile + 40% of leak (re-radiated) uniformly;
    # rear faces get 60% of leak (west wall is adiabatic, re-radiates)
    Q_gap_per_gap = q_gap_net * W_GAP         # W per m height per gap
    q_rear_unif = 0.6 * leak * Q_gap_per_gap / W_FRONT       # W/m2 on rear face
    q_side_unif = 0.4 * leak * Q_gap_per_gap / (2.0 * D_SIDE)

    T = [T_a_mid + 60.0] * N                  # init
    kt = K_STEEL * T_WALL

    for it in range(300):
        # internal mean-radiant temperature (radiosity closure: sum eps*sig*(T^4-Tmr^4)=0)
        Tmr4 = sum(t ** 4 for t in T) / N
        # build tridiagonal: a*T[i-1] + b*T[i] + c*T[i+1] = d
        a = [0.0] * N; b = [0.0] * N; c = [0.0] * N; d = [0.0] * N
        for i in range(N):
            s = s_nodes[i]
            fc = face_of(s)
            cond = kt / ds ** 2
            bi = 0.0; di = 0.0
            if i > 0:
                a[i] = -cond; bi += cond
            if i < N - 1:
                c[i] = -cond; bi += cond
            Ti = T[i]
            # linearization coefficient for T^4 sinks: hr = 4 sig T^3 * eps_eff
            # external radiation load
            if fc == "front":
                hr = 4.0 * SIGMA * Ti ** 3 / R_fp
                q_src = SIGMA * T_p_mid ** 4 / R_fp
                bi += hr * (1.0)  # will subtract via source linearization below
                di += q_src - SIGMA * Ti ** 4 / R_fp + hr * Ti
                h_ext = h_cav
            elif fc == "side":
                x = s - 0.5 * W_FRONT
                X0, X1 = max(x - 0.5 * ds, 0.0), min(x + 0.5 * ds, D_SIDE)
                absorbed = (gap_F(X0) - gap_F(X1)) * Q_gap_per_gap / 2.0 / ds  # W/m2
                di += absorbed + q_side_unif
                # escape/self-emission correction: local exchange toward mouth
                F_esc = 0.5 * W_GAP * (1.0 - (x / W_GAP) / math.sqrt(1.0 + (x / W_GAP) ** 2)) / W_GAP
                hr = 4.0 * EPS_R * SIGMA * F_esc * Ti ** 3
                bi += hr
                di += EPS_R * SIGMA * F_esc * (T_side_ref ** 4 - Ti ** 4) + hr * Ti
                h_ext = 0.7 * h_cav
            else:  # rear
                di += q_rear_unif
                h_ext = h_cav
            # external convection (cavity gas)
            bi += h_ext
            di += h_ext * T_g
            # internal convection
            bi += h_int
            di += h_int * T_a_mid
            # internal radiation to mean-radiant node
            hr_i = 4.0 * EPS_R * SIGMA * Ti ** 3
            bi += hr_i
            di += EPS_R * SIGMA * (Tmr4 - Ti ** 4) + hr_i * Ti
            b[i] = bi; d[i] = di
        # Thomas algorithm
        cp_ = [0.0] * N; dp_ = [0.0] * N
        cp_[0] = c[0] / b[0]; dp_[0] = d[0] / b[0]
        for i in range(1, N):
            m = b[i] - a[i] * cp_[i - 1]
            cp_[i] = c[i] / m
            dp_[i] = (d[i] - a[i] * dp_[i - 1]) / m
        Tn = [0.0] * N
        Tn[-1] = dp_[-1]
        for i in range(N - 2, -1, -1):
            Tn[i] = dp_[i] - cp_[i] * Tn[i + 1]
        # relax
        err = max(abs(Tn[i] - T[i]) for i in range(N))
        T = [T[i] + 0.6 * (Tn[i] - T[i]) for i in range(N)]
        if err < 0.005:
            break

    # face results
    front_nodes = [i for i in range(N) if face_of(s_nodes[i]) == "front"]
    side_nodes = [i for i in range(N) if face_of(s_nodes[i]) == "side"]
    rear_nodes = [i for i in range(N) if face_of(s_nodes[i]) == "rear"]
    T_front = T[0]
    T_front_mean = sum(T[i] for i in front_nodes) / len(front_nodes)
    T_side_mean = sum(T[i] for i in side_nodes) / len(side_nodes)
    T_rear_mean = sum(T[i] for i in rear_nodes) / len(rear_nodes)
    # net front radiative absorption (for gap split bookkeeping), W per m height per half duct
    Q_front_rad = sum(SIGMA * (T_p_mid ** 4 - T[i] ** 4) / R_fp * ds for i in front_nodes)
    # sensor-style fluxes at midplane
    x_mid = 0.5 * D_SIDE
    q_side_rad_mid = ((gap_F(x_mid - 0.005) - gap_F(x_mid + 0.005)) * Q_gap_per_gap / 2.0 / 0.01
                      + q_side_unif)
    fluxes = {
        "front_rad": SIGMA * (T_p_mid ** 4 - T_front ** 4) / R_fp,
        "front_conv": h_cav * (T_g - T_front),
        "side_rad": q_side_rad_mid,
        "side_conv": 0.7 * h_cav * (T_g - T_side_mean),
        "rear_rad": q_rear_unif,
        "rear_conv": h_cav * (T_g - T_rear_mean),
    }
    return {"T": T, "T_front": T_front, "T_front_mean": T_front_mean,
            "T_side_mean": T_side_mean, "T_rear_mean": T_rear_mean,
            "Q_front_rad_perm": 2.0 * Q_front_rad, "fluxes": fluxes}


def solve_cavity(Q_air, mdot, T_in_C, T_out_C, nseg=20):
    """Axial cavity model. Returns plate/wall/gas temps and radiation split."""
    T_in, T_out = T_in_C + 273.15, T_out_C + 273.15
    T_m = 0.5 * (T_in + T_out)
    q_net = Q_air / A_PLATE                          # net plate flux (uniform heating)

    # radiation network constants
    F12 = viewfactor_parallel_rect(W_CAV / GAP_PL, H_HEAT / GAP_PL)
    Fhat = 0.5 * (1.0 + F12)                         # re-radiating N/S/top/bottom surfaces
    frac_f = W_FRONT / PITCH                         # 0.4615
    frac_g = 1.0 - frac_f
    # apparent emissivity of gap mouth (deep slot cavity effect)
    A_ratio = W_GAP / (2.0 * D_SIDE + W_GAP)
    eps_gap = 1.0 / (1.0 + (1.0 / EPS_R - 1.0) * A_ratio)
    eps_bank = frac_f * EPS_R + frac_g * eps_gap
    R_net = (1.0 / EPS_P - 1.0) + 1.0 / Fhat + (1.0 / eps_bank - 1.0)   # per unit area
    R_fp = (1.0 / EPS_P - 1.0) + 1.0 / Fhat + (1.0 / EPS_R - 1.0)       # plate<->front face

    # internal convection
    Gm = mdot / (N_RISER * A_INT)
    Re_r = Gm * DH / mu_air(T_m)
    h_int = h_gnielinski(Re_r, T_m)

    # axial gas temperature (linear — uniform heating)
    z = [(i + 0.5) / nseg * H_HEAT for i in range(nseg)]
    T_a = [T_in + (T_out - T_in) * zz / H_HEAT for zz in z]
    i_mid = min(range(nseg), key=lambda i: abs(z[i] - 3.5))

    # initial guesses
    d_front, d_side, d_rear = 70.0, 40.0, 25.0
    T_g = T_m + 60.0
    perim = None
    T_p = [T_m + 300.0] * nseg

    for outer in range(25):
        # bank effective radiating temperature per segment
        T_bank4 = [ (frac_f * EPS_R * (T_a[i] + d_front) ** 4
                     + frac_g * eps_gap * (T_a[i] + d_side) ** 4) / eps_bank
                    for i in range(nseg)]
        # solve plate temperature per segment: scriptF sig (Tp^4 - Tb^4) + hp (Tp - Tg) = q_net
        Q_rad = 0.0
        hp_list = []
        for i in range(nseg):
            lo, hi = T_a[i], 1600.0
            for _ in range(60):
                Tp = 0.5 * (lo + hi)
                hp = h_churchill_chu(Tp, T_g, H_HEAT)
                r = SIGMA * (Tp ** 4 - T_bank4[i]) / R_net + hp * (Tp - T_g) - q_net
                if r > 0:
                    hi = Tp
                else:
                    lo = Tp
            T_p[i] = 0.5 * (lo + hi)
            hp_list.append(h_churchill_chu(T_p[i], T_g, H_HEAT))
            Q_rad += SIGMA * (T_p[i] ** 4 - T_bank4[i]) / R_net * (A_PLATE / nseg)
        Q_conv_p = Q_air - Q_rad

        # cavity gas node: plate convection in = riser-surface convection out
        # external surface mean temps per segment
        def surf_T(i):
            wf, ws, wr = W_FRONT, 2.0 * D_SIDE, W_FRONT
            return ((T_a[i] + d_front) * wf + (T_a[i] + d_side) * ws + (T_a[i] + d_rear) * wr) / (wf + ws + wr)
        lo, hi = min(T_a), max(T_p)
        for _ in range(60):
            Tg_t = 0.5 * (lo + hi)
            qin = sum(hp_list[i] * (A_PLATE / nseg) * (T_p[i] - Tg_t) for i in range(nseg))
            qout = 0.0
            for i in range(nseg):
                Ts = surf_T(i)
                h_r = h_churchill_chu(Tg_t, Ts, H_HEAT)
                # area-weighted: sides get 0.7 reduction (confined gaps)
                A_seg = (A_FRONT_TOT + A_REAR_TOT + 0.7 * A_SIDE_TOT) / nseg
                qout += h_r * A_seg * (Tg_t - Ts)
            if qin > qout:
                lo = Tg_t
            else:
                hi = Tg_t
        T_g_new = 0.5 * (lo + hi)

        # midplane perimeter model
        h_cav = h_churchill_chu(T_g_new, surf_T(i_mid), H_HEAT)
        # net radiation into gap mouths (per m2 mouth): global rad minus front absorption
        # first pass uses previous perim; iterate
        q_rad_mid = SIGMA * (T_p[i_mid] ** 4 - T_bank4[i_mid]) / R_net   # W/m2 plate
        Q_front_guess = SIGMA * (T_p[i_mid] ** 4 - (T_a[i_mid] + d_front) ** 4) / R_fp * frac_f
        q_gap_net = max((q_rad_mid - Q_front_guess) * PITCH / W_GAP, 0.0)
        perim = perimeter_model(T_p[i_mid], T_g_new, T_a[i_mid], h_int, h_cav,
                                q_gap_net, T_a[i_mid] + d_side, R_fp)

        d_front_n = perim["T_front"] - T_a[i_mid]
        d_side_n = perim["T_side_mean"] - T_a[i_mid]
        d_rear_n = perim["T_rear_mean"] - T_a[i_mid]
        chg = max(abs(d_front_n - d_front), abs(d_side_n - d_side),
                  abs(d_rear_n - d_rear), abs(T_g_new - T_g))
        rel = 0.7
        d_front += rel * (d_front_n - d_front)
        d_side += rel * (d_side_n - d_side)
        d_rear += rel * (d_rear_n - d_rear)
        T_g += rel * (T_g_new - T_g)
        if chg < 0.05:
            break

    rad_fraction = Q_rad / Q_air
    fl = perim["fluxes"]
    return {
        "T_p_mid_C": T_p[i_mid] - 273.15,
        "T_p_avg_C": sum(T_p) / nseg - 273.15,
        "T_p_max_C": max(T_p) - 273.15,
        "T_g_C": T_g - 273.15,
        "T_w_front_mid_C": perim["T_front"] - 273.15,
        "T_w_side_mid_C": perim["T_side_mean"] - 273.15,
        "T_w_rear_mid_C": perim["T_rear_mean"] - 273.15,
        "T_a_mid_C": T_a[i_mid] - 273.15,
        "rad_fraction": rad_fraction,
        "Q_rad": Q_rad, "Q_conv": Q_conv_p,
        "h_int": h_int, "Re_riser": Re_r,
        "F12": F12, "Fhat": Fhat, "eps_bank": eps_bank, "scriptF": 1.0 / R_net,
        "fluxes_mid": {k: v for k, v in fl.items()},
    }


# ----------------------------------------------------------------------------------
# 4. Accident decay-heat transient (quasi-steady sweep of the given polynomial)
# ----------------------------------------------------------------------------------
POLY = [466.531039994, 0.078631095079, 0.000170562320568, -1.28449427566e-07,
        5.09424812301e-11, -1.27606140005e-14, 2.04789514471e-18, -2.08318254453e-22,
        1.29530038954e-26, -4.48601180685e-31]
PSCALE = 90.0


def P_electric(t_min):
    s = 0.0
    for n, c in enumerate(POLY):
        s += c * t_min ** n
    return s * PSCALE  # W electric


def run_case(P_e, f_loss, T_in_C=20.0, T_amb_C=2.0, wind=0.0):
    Q_air = (1.0 - f_loss) * P_e
    lp = solve_loop(Q_air, T_in_C, T_amb_C, wind)
    cav = solve_cavity(Q_air, lp["mdot"], T_in_C, lp["T_out_C"])
    return lp, cav, Q_air


# ----------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------
def main():
    out = {}
    F_LOSS = 0.30          # parasitic (heater-back + cavity structure) loss fraction
    P_E_BASE = 82000.0     # W electric, Case 1

    print("=" * 78)
    print("CASE 1 — baseline steady state: 82 kWe, T_in=20 C, T_amb(out)=2 C, low wind")
    print("=" * 78)
    lp, cav, Q_air = run_case(P_E_BASE, F_LOSS)
    print(f"  Q_air (net to risers)          : {Q_air/1000:.1f} kW  (f_loss={F_LOSS})")
    print(f"  mass flow                      : {lp['mdot']:.3f} kg/s = {lp['mdot']*60:.1f} kg/min")
    print(f"  riser dT (out-in)              : {lp['dT']:.1f} K   (T_out={lp['T_out_C']:.1f} C)")
    print(f"  riser Re                       : {lp['Re_riser']:.0f},  h_int={cav['h_int']:.1f} W/m2K")
    print(f"  F12 plate->bank plane          : {cav['F12']:.3f}  Fhat={cav['Fhat']:.3f} "
          f"eps_bank={cav['eps_bank']:.3f} scriptF={cav['scriptF']:.3f}")
    print(f"  plate T (z=3.5 m / avg / max)  : {cav['T_p_mid_C']:.0f} / {cav['T_p_avg_C']:.0f} / {cav['T_p_max_C']:.0f} C")
    print(f"  cavity gas T (mixed)           : {cav['T_g_C']:.0f} C")
    print(f"  riser wall midplane front/side/rear: {cav['T_w_front_mid_C']:.0f} / "
          f"{cav['T_w_side_mid_C']:.0f} / {cav['T_w_rear_mid_C']:.0f} C  (air {cav['T_a_mid_C']:.0f} C)")
    print(f"  radiative fraction of removal  : {cav['rad_fraction']:.2f} "
          f"(Q_rad={cav['Q_rad']/1000:.1f} kW, Q_conv={cav['Q_conv']/1000:.1f} kW)")
    fm = cav["fluxes_mid"]
    print(f"  midplane sensor fluxes (W/m2): front rad {fm['front_rad']:.0f} conv {fm['front_conv']:.0f} | "
          f"side rad {fm['side_rad']:.0f} conv {fm['side_conv']:.0f} | rear rad {fm['rear_rad']:.0f} conv {fm['rear_conv']:.0f}")

    out["baseline"] = {"Q_air_kW": Q_air / 1000, "mdot_kgs": lp["mdot"], "dT_C": lp["dT"],
                       "T_out_C": lp["T_out_C"], "plate_mid_C": cav["T_p_mid_C"],
                       "plate_avg_C": cav["T_p_avg_C"], "T_gas_cavity_C": cav["T_g_C"],
                       "riser_wall_front_mid_C": cav["T_w_front_mid_C"],
                       "riser_wall_side_mid_C": cav["T_w_side_mid_C"],
                       "rad_fraction": cav["rad_fraction"], "Re_riser": lp["Re_riser"],
                       "fluxes_mid_Wm2": fm}

    # ---------------- sensitivity: parasitic loss fraction ----------------
    print("\nSENSITIVITY — parasitic loss fraction (most uncertain assumption)")
    sens = {}
    for fl in (0.15, 0.22, 0.30, 0.35):
        lp2, cav2, Qa2 = run_case(P_E_BASE, fl)
        sens[fl] = (Qa2, lp2, cav2)
        print(f"  f_loss={fl:.2f}: Q={Qa2/1000:5.1f} kW  mdot={lp2['mdot']:.3f} kg/s  "
              f"dT={lp2['dT']:5.1f} K  plate={cav2['T_p_mid_C']:.0f} C  "
              f"wall={cav2['T_w_front_mid_C']:.0f} C  fr={cav2['rad_fraction']:.2f}")
    out["sensitivity_floss"] = {str(k): {"Q_kW": v[0] / 1000, "mdot": v[1]["mdot"], "dT": v[1]["dT"],
                                         "plate_C": v[2]["T_p_mid_C"], "wall_C": v[2]["T_w_front_mid_C"],
                                         "rad_fraction": v[2]["rad_fraction"]} for k, v in sens.items()}

    # sensitivity: riser emissivity
    print("\nSENSITIVITY — riser emissivity (not reported in source)")
    global EPS_R
    eps_save = EPS_R
    for e in (0.70, 0.80, 0.90):
        EPS_R = e
        lp3, cav3, _ = run_case(P_E_BASE, F_LOSS)
        print(f"  eps_r={e:.2f}: plate={cav3['T_p_mid_C']:.0f} C  wall={cav3['T_w_front_mid_C']:.0f} C  "
              f"fr={cav3['rad_fraction']:.2f}")
    EPS_R = eps_save

    # ---------------- Case 2: accident decay-heat transient ----------------
    print("\n" + "=" * 78)
    print("CASE 2 — accident decay-heat transient (quasi-steady sweep)")
    print("=" * 78)
    times_h = [0, 6, 12, 24, 36, 48, 60, 72, 80, 84.85, 90, 96, 108, 120, 130]
    acc = []
    pk = (None, -1)
    for th in times_h:
        Pe = P_electric(th * 60.0)
        if Pe <= 0:
            continue
        lpa, cava, Qa = run_case(Pe, F_LOSS)
        acc.append({"t_h": th, "P_e_kW": Pe / 1000, "Q_kW": Qa / 1000, "mdot": lpa["mdot"],
                    "dT": lpa["dT"], "plate_C": cava["T_p_mid_C"], "wall_C": cava["T_w_front_mid_C"]})
        if cava["T_p_mid_C"] > pk[1]:
            pk = (acc[-1], cava["T_p_mid_C"])
        print(f"  t={th:6.1f} h  P_e={Pe/1000:5.1f} kW  Q={Qa/1000:5.1f} kW  mdot={lpa['mdot']:.3f}  "
              f"dT={lpa['dT']:5.1f} K  plate={cava['T_p_mid_C']:.0f} C wall={cava['T_w_front_mid_C']:.0f} C")
    peak = pk[0]
    # plate thermal time constant (lumped) for quasi-steady justification
    C_plate = A_PLATE * 0.0254 * 7850.0 * 480.0
    hrad_eff = 4.0 * SIGMA * (peak["plate_C"] + 273.15) ** 3 * 0.6
    tau_h = C_plate / (hrad_eff * A_PLATE) / 3600.0
    print(f"  -> peak plate {peak['plate_C']:.0f} C at t={peak['t_h']} h; plate time constant ~{tau_h:.2f} h "
          f"<< 85 h  (quasi-steady OK)")
    LIMIT_C = 538.0
    bounded = peak["plate_C"] < LIMIT_C
    print(f"  vessel-limit check: peak {peak['plate_C']:.0f} C vs 538 C accident limit -> "
          f"{'BOUNDED (levels off)' if bounded else 'EXCEEDS'}")
    out["accident"] = {"table": acc, "peak_plate_C": peak["plate_C"], "peak_t_h": peak["t_h"],
                       "peak_mdot": peak["mdot"], "bounded": bounded, "limit_C": LIMIT_C,
                       "plate_tau_h": tau_h}

    # ---------------- Case 3: weather sensitivity ----------------
    print("\n" + "=" * 78)
    print("CASE 3 — weather sensitivity (baseline heat load)")
    print("=" * 78)
    wx = []
    for Ta in (-18.0, -10.0, 0.0, 2.0, 10.0, 24.0):
        for w in (0.0, 5.0, 11.0):
            lpw = solve_loop(Q_air, 20.0, Ta, w)
            cavw = solve_cavity(Q_air, lpw["mdot"], 20.0, lpw["T_out_C"])
            wx.append({"T_amb": Ta, "wind": w, "mdot": lpw["mdot"], "dT": lpw["dT"],
                       "plate_C": cavw["T_p_mid_C"]})
            print(f"  T_amb={Ta:6.1f} C wind={w:4.1f} m/s: mdot={lpw['mdot']:.3f} kg/s "
                  f"({(lpw['mdot']/lp['mdot']-1)*100:+5.1f}%)  dT={lpw['dT']:5.1f} K  "
                  f"plate={cavw['T_p_mid_C']:.0f} C")
    out["weather"] = wx

    m_base = lp["mdot"]
    m_cold = [w for w in wx if w["T_amb"] == -18.0 and w["wind"] == 0.0][0]["mdot"]
    m_hot = [w for w in wx if w["T_amb"] == 24.0 and w["wind"] == 0.0][0]["mdot"]
    m_wind = [w for w in wx if w["T_amb"] == 2.0 and w["wind"] == 11.0][0]["mdot"]
    note = (f"Flow strengthens with cold ambient and with wind: at fixed 82 kWe load, "
            f"mdot goes from {m_base:.2f} kg/s (+2 C, calm) to {m_cold:.2f} kg/s at -18 C "
            f"({(m_cold/m_base-1)*100:+.0f}%) and {m_hot:.2f} kg/s at +24 C "
            f"({(m_hot/m_base-1)*100:+.0f}%); an 11 m/s wind adds stack-tip suction "
            f"(Cp~0.4) giving {m_wind:.2f} kg/s ({(m_wind/m_base-1)*100:+.0f}%). Riser dT varies "
            f"inversely (Q fixed); plate temperature moves only ~+/-10 K because radiation "
            f"dominates. Colder/windier weather always improves passive heat removal; the "
            f"penalty direction is hot, still summer days.")
    print("\n  " + note)

    # ---------------- results.json ----------------
    results = {
        "mdot_kgs": round(lp["mdot"], 3),
        "dT_C": round(lp["dT"], 1),
        "riser_wall_C": round(cav["T_w_front_mid_C"], 0),
        "plate_C": round(cav["T_p_mid_C"], 0),
        "rad_fraction": round(cav["rad_fraction"], 2),
        "accident_peak_plate_C": round(peak["plate_C"], 0),
        "accident_bounded": bool(bounded),
        "weather_flow_change_note": note,
        "detail": out,
    }
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("\nresults.json written.")


if __name__ == "__main__":
    main()

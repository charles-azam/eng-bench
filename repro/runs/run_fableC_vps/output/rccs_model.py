"""Quasi-2D natural-circulation model of the 1/2-scale air-cooled RCCS facility.

Physics
-------
* Cavity radiation: per-axial-slice radiosity network, 5 surface groups
  (heated plate, riser front faces, riser side faces, riser rear faces,
  insulated cavity walls) with Monte-Carlo view factors (viewfactors.py).
* Cavity gas convection: Churchill-Chu vertical-surface natural convection
  (Churchill & Chu 1975; Incropera eq. 9.26) between plate / riser exterior
  faces / walls and a well-mixed cavity-air node.
* Riser internal convection: Gnielinski (1976) with a (Tw/Tb)^-0.5
  property-ratio correction for gas heating (Kays & Crawford).
* Duct wall: per-face nodes coupled by wall conduction and by internal
  front<->rear radiation.
* Loop hydraulics: buoyancy integral over downcomer / risers / outlet
  plenum / chimney vs. friction (Petukhov smooth-tube) + form losses
  (Idelchik-style K values). Mass flow from the 1-D momentum balance.
* Parasitic losses: conduction through the heater back board and through
  the 6-in SuperIsol cavity-wall insulation (solved consistently as a
  radiating/convecting inner wall surface).

All dimensions from inputs/01, materials from inputs/02.
"""
import numpy as np
from scipy.optimize import brentq, root
import airprops as air
from viewfactors import get_F

SIG = 5.670374419e-8
G = 9.81
FORM_SCALE = 1.0               # multiplier on all form-loss K values
                               # (sensitivity-study hook)

# ---------------------------------------------------------------- geometry
N_SL = 10                      # axial slices (match 10 heater zones)
L_HEAT = 6.91                  # riser length inside heated cavity, m (272 in)
L_RISER = 7.49                 # total riser length, m (295 in)
W_CAV = 1.3208                 # cavity width, m
H_PLATE = 6.7                  # heated plate height, m (used for Ra length)
A_PLATE = W_CAV * L_HEAT       # 9.13 m^2, consistent with the radiosity
                               # slices (source lists 8.82 scaled / 10.18
                               # as-built; geometric envelope 8.85-9.13)
EPS_PLATE = 0.785              # measured 0.78-0.79
EPS_RISER = 0.80               # oxidized structural steel (assumed, +-0.10)
EPS_WALL = 0.85                # board insulation surface (assumed)

# riser duct (per duct)
DUCT_WI = 0.04125              # internal narrow dimension, m (1.624 in)
DUCT_DI = 0.24445              # internal wide dimension, m (9.624 in)
T_WALL = 0.004775              # wall, m (0.188 in)
K_STEEL = 50.0
A_INT = DUCT_WI * DUCT_DI      # 0.010083 m^2
PER_INT = 2 * (DUCT_WI + DUCT_DI)
DH = 4 * A_INT / PER_INT       # 0.0706 m
N_DUCT = 12
A_FLOW = N_DUCT * A_INT        # 0.121 m^2

# exterior / interior per-unit-height widths per face group (all 12 ducts)
W_EXT = np.array([N_DUCT * 0.0508, 2 * N_DUCT * 0.254, N_DUCT * 0.0508])
W_INT = np.array([N_DUCT * DUCT_WI, 2 * N_DUCT * DUCT_DI, N_DUCT * DUCT_WI])

# wall conduction between face groups, W/K per m of height (all ducts):
# 2 paths per duct per junction, path length = half front + half side face
COND_FS = N_DUCT * 2 * K_STEEL * T_WALL / (0.0508 / 2 + 0.254 / 2)
COND_RS = COND_FS

# internal front<->rear radiation: parallel strips
EPS_IN = 1.0 / (1 / 0.8 + 1 / 0.8 - 1)
F_FR_IN = 0.82

# loop elevations (z above inlet-plenum floor), m
Z_RISER_IN = 0.94
Z_HEAT_BOT = 1.12
Z_RISER_TOP = Z_RISER_IN + L_RISER            # 8.43
Z_CHIM_PORT = (Z_RISER_TOP - 0.406) + 1.435   # 9.46
Z_DISCHARGE = 19.6
Z_DC_IN = 4.0                                 # downcomer inlet elev (assumed)

A_DC = np.pi * 0.61 ** 2 / 4
L_DC = 4.69
K_DC = 2.3
K_RISER_IN = 0.8
K_RISER_OUT = 1.0
A_CHIM = 0.58
A_STACK = A_CHIM / 2
L_CHIM = 32.9
D_CHIM = 0.61
K_CHIM = 0.5 + 0.75 + 1.0
UA_CHIM_PER_M = 1.06           # W/K per m per stack (3-in Enerwrap + films)
L_CHIM_VERT = Z_DISCHARGE - Z_CHIM_PORT

A_CAVWALL = (2 * 1.0106 + W_CAV) * L_HEAT     # N/S/W inner faces, ~23.1 m^2
TH_ISO = 0.152
TH_DUR = 0.0508
EPS_EFF_HTR = 1.0 / (1 / 0.90 + 1 / EPS_PLATE - 1)
H_OUT = 8.0

DZ = L_HEAT / N_SL
F_MAT, AREAS = get_F()
EPS_VEC = np.array([EPS_PLATE, EPS_RISER, EPS_RISER, EPS_RISER, EPS_WALL])
A_FR_IN = W_INT[0] * DZ         # internal front-face area per slice


def k_superisol(T):
    return np.interp(T, [473, 673, 873], [0.060, 0.080, 0.100])


def k_duraboard(T):
    return np.interp(T, [477, 811], [0.079, 0.122])


def fric(Re):
    Re = max(Re, 100.0)
    if Re < 2300:
        return 64.0 / Re
    return (0.790 * np.log(Re) - 1.64) ** -2


def nu_churchill_chu(dT, T_film, L):
    dT = max(abs(dT), 0.01)
    T_film = min(max(T_film, 220.0), 2500.0)
    nu_k = air.mu(T_film) / air.rho(T_film)
    Pr = air.Pr(T_film)
    Ra = G * dT * L ** 3 / (T_film * nu_k * (nu_k / Pr))
    Nu = (0.825 + 0.387 * Ra ** (1 / 6)
          / (1 + (0.492 / Pr) ** (9 / 16)) ** (8 / 27)) ** 2
    return Nu * air.k(T_film) / L


def h_int_gnielinski(m_dot, T_b, T_w):
    Gm = m_dot / A_FLOW
    Re = Gm * DH / air.mu(T_b)
    Pr = air.Pr(T_b)
    if Re < 2300:
        Nu = 4.36
    else:
        f = fric(Re)
        Nu = (f / 8) * (Re - 1000) * Pr / (
            1 + 12.7 * np.sqrt(f / 8) * (Pr ** (2 / 3) - 1))
    Nu *= (max(T_w, T_b + 1) / T_b) ** -0.5
    return Nu * air.k(T_b) / DH, Re


def rad_solve(T5):
    """net radiative flux LEAVING each surface group, all temps given."""
    A = np.eye(5) - (1 - EPS_VEC)[:, None] * F_MAT
    b = EPS_VEC * SIG * np.asarray(T5) ** 4
    J = np.linalg.solve(A, b)
    return J - F_MAT @ J


def slice_solve(q_pl, T_air, T_cav, T_bldg, h_i, x0, T_plate_fixed=None):
    """Solve one axial slice.

    Unknowns: Tp, Tf, Ts, Tr, Tw  (plate, riser front/side/rear, wall inner).
    q_pl: imposed net plate heat flux (W/m^2) or None if T_plate_fixed.
    Returns solution dict.
    """
    A_wall_sl = A_CAVWALL / N_SL

    def eqs(x):
        if T_plate_fixed is None:
            Tp, Tf, Ts, Tr, Tw = x
        else:
            Tp = T_plate_fixed
            Tf, Ts, Tr, Tw = x
        q = rad_solve([Tp, Tf, Ts, Tr, Tw])
        h_pl = nu_churchill_chu(Tp - T_cav, (Tp + T_cav) / 2, H_PLATE)
        h_f = nu_churchill_chu(Tf - T_cav, (Tf + T_cav) / 2, H_PLATE)
        h_s = nu_churchill_chu(Ts - T_cav, (Ts + T_cav) / 2, H_PLATE)
        h_r = nu_churchill_chu(Tr - T_cav, (Tr + T_cav) / 2, H_PLATE)
        h_w = nu_churchill_chu(T_cav - Tw, (Tw + T_cav) / 2, H_PLATE)
        q_fr = EPS_IN * F_FR_IN * SIG * (Tf ** 4 - Tr ** 4)
        U_w = 1.0 / (TH_ISO / k_superisol(max(Tw, 300.0)) + 1 / H_OUT)
        r = np.empty(5 if T_plate_fixed is None else 4)
        i = 0
        if T_plate_fixed is None:
            r[i] = q_pl - q[0] - h_pl * (Tp - T_cav)
            i += 1
        r[i] = (-q[1] * W_EXT[0] * DZ + h_f * W_EXT[0] * DZ * (T_cav - Tf)
                + COND_FS * DZ * (Ts - Tf) - q_fr * A_FR_IN
                - h_i * W_INT[0] * DZ * (Tf - T_air))
        r[i + 1] = (-q[2] * W_EXT[1] * DZ + h_s * W_EXT[1] * DZ * (T_cav - Ts)
                    - COND_FS * DZ * (Ts - Tf) - COND_RS * DZ * (Ts - Tr)
                    - h_i * W_INT[1] * DZ * (Ts - T_air))
        r[i + 2] = (-q[3] * W_EXT[2] * DZ + h_r * W_EXT[2] * DZ * (T_cav - Tr)
                    + COND_RS * DZ * (Ts - Tr) + q_fr * A_FR_IN
                    - h_i * W_INT[2] * DZ * (Tr - T_air))
        r[i + 3] = (-q[4] + h_w * (T_cav - Tw) - U_w * (Tw - T_bldg))
        return r / 100.0

    sol = root(eqs, x0, method="hybr", options=dict(xtol=1e-10))
    x = sol.x
    if T_plate_fixed is None:
        Tp, Tf, Ts, Tr, Tw = x
    else:
        Tp = T_plate_fixed
        Tf, Ts, Tr, Tw = x
    q = rad_solve([Tp, Tf, Ts, Tr, Tw])
    h_pl = nu_churchill_chu(Tp - T_cav, (Tp + T_cav) / 2, H_PLATE)
    h_f = nu_churchill_chu(Tf - T_cav, (Tf + T_cav) / 2, H_PLATE)
    h_s = nu_churchill_chu(Ts - T_cav, (Ts + T_cav) / 2, H_PLATE)
    h_r = nu_churchill_chu(Tr - T_cav, (Tr + T_cav) / 2, H_PLATE)
    h_w = nu_churchill_chu(T_cav - Tw, (Tw + T_cav) / 2, H_PLATE)
    U_w = 1.0 / (TH_ISO / k_superisol(max(Tw, 300.0)) + 1 / H_OUT)
    A_wall_sl = A_CAVWALL / N_SL
    out = dict(
        ok=sol.success, x=x, Tp=Tp, Tf=Tf, Ts=Ts, Tr=Tr, Tw=Tw,
        q_rad=q,
        Q_pl_conv=h_pl * (Tp - T_cav) * (A_PLATE / N_SL),
        Q_ris_conv=DZ * (h_f * W_EXT[0] * (T_cav - Tf)
                         + h_s * W_EXT[1] * (T_cav - Ts)
                         + h_r * W_EXT[2] * (T_cav - Tr)),
        Q_wall_conv=h_w * A_wall_sl * (T_cav - Tw),
        Q_wall_loss=U_w * A_wall_sl * (Tw - T_bldg),
        Q_rad_ris=-DZ * (q[1] * W_EXT[0] + q[2] * W_EXT[1] + q[3] * W_EXT[2]),
        Q_conv_ris_ext=DZ * (h_f * W_EXT[0] * (T_cav - Tf)
                             + h_s * W_EXT[1] * (T_cav - Ts)
                             + h_r * W_EXT[2] * (T_cav - Tr)),
        q_face_rad=(-q[1], -q[2], -q[3]),
        q_face_conv=(h_f * (T_cav - Tf), h_s * (T_cav - Ts),
                     h_r * (T_cav - Tr)),
        h_pl=h_pl,
    )
    out["Q_air"] = h_i * DZ * float(W_INT @ np.array(
        [Tf - T_air, Ts - T_air, Tr - T_air]))
    return out


def solve_thermal(m_dot, P_to_plate, T_in, T_bldg, T_plate_fixed=None):
    """March the heated section for a given loop mass flow; find cavity-air
    temperature from the cavity gas heat balance."""
    q_pl = None if T_plate_fixed is None else None
    if T_plate_fixed is None:
        q_pl = P_to_plate / A_PLATE

    state = {}

    def march(T_cav):
        T_air = T_in
        prof = []
        if T_plate_fixed is None:
            x0 = np.array([T_cav + 150, T_air + 60, T_air + 50, T_air + 30,
                           T_cav - 20])
        else:
            x0 = np.array([T_air + 60, T_air + 50, T_air + 30, T_cav - 20])
        for i in range(N_SL):
            h_i, Re = h_int_gnielinski(m_dot, T_air,
                                       T_air + 40 if not prof else prof[-1]["Tf"])
            s = slice_solve(q_pl, T_air, T_cav, T_bldg, h_i, x0,
                            T_plate_fixed)
            x0 = s["x"]
            s.update(z=(i + 0.5) * DZ, Tair=T_air, h_i=h_i, Re=Re)
            prof.append(s)
            T_air = T_air + s["Q_air"] / (m_dot * air.cp(T_air))
        state["prof"] = prof
        state["T_out"] = T_air
        return prof

    def resid(T_cav):
        prof = march(T_cav)
        return (sum(p["Q_pl_conv"] for p in prof)
                - sum(p["Q_ris_conv"] for p in prof)
                - sum(p["Q_wall_conv"] for p in prof))

    # bracket: cavity air between inlet air temp and ~plate temp
    lo, hi = T_in + 0.5, 1600.0
    r_lo = resid(lo)
    Tg = np.linspace(lo, hi, 25)
    br = None
    rp = (lo, r_lo)
    for Tc in Tg[1:]:
        r = resid(Tc)
        if np.isfinite(r) and np.isfinite(rp[1]) and r * rp[1] < 0:
            br = (rp[0], Tc)
            break
        rp = (Tc, r)
    if br is None:
        raise RuntimeError(f"no cavity-air balance root (m={m_dot:.3f})")
    T_cav = brentq(resid, *br, xtol=0.05)
    prof = march(T_cav)
    return dict(
        T_cav=T_cav, prof=prof, T_out=state["T_out"],
        Q_removed=sum(p["Q_air"] for p in prof),
        Q_wall=sum(p["Q_wall_loss"] for p in prof),
        Q_rad_risers=sum(p["Q_rad_ris"] for p in prof),
        Q_conv_risers=sum(p["Q_conv_ris_ext"] for p in prof),
        Q_plate_conv=sum(p["Q_pl_conv"] for p in prof),
        Q_plate_total=(P_to_plate if T_plate_fixed is None else
                       sum(p["q_rad"][0] * (A_PLATE / N_SL) + p["Q_pl_conv"]
                           for p in prof)),
    )


def loop_dp(m_dot, therm, T_in, T_out_gas, T_amb, wind=0.0, cp_wind=0.0):
    """buoyancy minus losses, Pa (positive accelerates the flow)."""
    rho_amb = air.rho(T_amb)
    rho_in = air.rho(T_in)

    drive = rho_amb * G * (Z_DISCHARGE - Z_DC_IN)
    drive += rho_in * G * (Z_DC_IN - Z_RISER_IN)
    col = 0.0
    col += air.rho(T_in) * (Z_HEAT_BOT - Z_RISER_IN)
    for p in therm["prof"]:
        col += air.rho(p["Tair"]) * DZ
    col += air.rho(T_out_gas) * (Z_RISER_TOP - (Z_HEAT_BOT + L_HEAT))
    col += air.rho(T_out_gas) * (Z_CHIM_PORT - Z_RISER_TOP)
    T = T_out_gas
    nz = 20
    dzc = L_CHIM_VERT / nz
    cp = air.cp(T_out_gas)
    for _ in range(nz):
        col += air.rho(T) * dzc
        T -= UA_CHIM_PER_M * dzc * (T - T_amb) / ((m_dot / 2) * cp)
    T_stack_exit = T
    drive -= col * G
    drive -= cp_wind * 0.5 * rho_amb * wind ** 2

    dp = 0.0
    ks = FORM_SCALE
    v_dc = m_dot / (rho_in * A_DC)
    Re_dc = rho_in * v_dc * 0.61 / air.mu(T_in)
    dp += (fric(Re_dc) * L_DC / 0.61 + ks * K_DC) * 0.5 * rho_in * v_dc ** 2
    Gm = m_dot / A_FLOW
    dp += ks * K_RISER_IN * 0.5 * Gm ** 2 / rho_in
    for p in therm["prof"]:
        rho_l = air.rho(p["Tair"])
        Re = Gm * DH / air.mu(p["Tair"])
        dp += fric(Re) * (DZ / DH) * Gm ** 2 / (2 * rho_l)
    rho_o = air.rho(T_out_gas)
    dp += fric(Gm * DH / air.mu(T_in)) * (0.18 / DH) * Gm ** 2 / (2 * rho_in)
    dp += fric(Gm * DH / air.mu(T_out_gas)) * (0.40 / DH) * Gm ** 2 / (2 * rho_o)
    dp += Gm ** 2 * (1 / rho_o - 1 / rho_in)
    dp += ks * K_RISER_OUT * 0.5 * Gm ** 2 / rho_o
    v_ch = (m_dot / 2) / (rho_o * A_STACK)
    Re_ch = rho_o * v_ch * D_CHIM / air.mu(T_out_gas)
    dp += (fric(Re_ch) * L_CHIM / D_CHIM + ks * K_CHIM) * 0.5 * rho_o * v_ch ** 2

    return drive - dp, T_stack_exit


def solve_steady(P_elec=None, T_outdoor=275.15, T_bldg=293.15,
                 T_inlet=None, wind=0.0, cp_wind=0.0, T_plate_fixed=None,
                 verbose=False):
    """Full coupled solve. Either P_elec (W) or T_plate_fixed (K) given."""
    T_in = T_inlet if T_inlet is not None else T_bldg

    Q_back = 0.0
    result = None
    for outer in range(10):
        P_to_plate = None if T_plate_fixed is not None else P_elec - Q_back

        def mom_residual(m_dot):
            try:
                th = solve_thermal(m_dot, P_to_plate, T_in, T_bldg,
                                   T_plate_fixed=T_plate_fixed)
            except RuntimeError:
                return np.nan
            r, _ = loop_dp(m_dot, th, T_in, th["T_out"], T_outdoor,
                           wind, cp_wind)
            return r

        grid = np.geomspace(0.08, 5.0, 20)
        r_prev, m_prev, bracket = None, None, None
        for mg in grid:
            r = mom_residual(mg)
            if not np.isfinite(r):
                r_prev, m_prev = None, None
                continue
            if r_prev is not None and r * r_prev < 0:
                bracket = (m_prev, mg)
                break
            r_prev, m_prev = r, mg
        if bracket is None:
            raise RuntimeError("no momentum-balance root found")
        m_dot = brentq(mom_residual, *bracket, xtol=1e-4)
        th = solve_thermal(m_dot, P_to_plate, T_in, T_bldg,
                           T_plate_fixed=T_plate_fixed)
        _, T_stack_exit = loop_dp(m_dot, th, T_in, th["T_out"], T_outdoor,
                                  wind, cp_wind)
        Tp_mean = np.mean([p["Tp"] for p in th["prof"]])
        if T_plate_fixed is None:
            q_gross = (P_elec - Q_back) / A_PLATE
            T_pb = Tp_mean + q_gross * 0.0254 / K_STEEL
            T_h = (T_pb ** 4 + q_gross / (SIG * EPS_EFF_HTR)) ** 0.25
            R_back = TH_DUR / k_duraboard((T_h + T_bldg) / 2) + 1 / H_OUT
            Q_back_new = A_PLATE * (T_h - T_bldg) / R_back
        else:
            T_h = Tp_mean
            Q_back_new = Q_back
        done = abs(Q_back_new - Q_back) < 20
        Q_back = 0.5 * (Q_back + Q_back_new)
        result = (m_dot, th, T_stack_exit, T_h)
        if done and outer >= 1:
            break

    m_dot, th, T_stack_exit, T_h = result
    prof = th["prof"]
    Tp_mean = np.mean([p["Tp"] for p in prof])
    zs = np.array([p["z"] for p in prof])

    def midp(key, idx=None):
        v = [p[key] if idx is None else p[key][idx] for p in prof]
        return float(np.interp(3.5, zs, v))

    out = dict(
        m_dot=m_dot, T_in=T_in, T_out=th["T_out"], dT=th["T_out"] - T_in,
        T_cav=th["T_cav"], Q_removed=th["Q_removed"], Q_back=Q_back,
        Q_wall=th["Q_wall"], Tp_mean=Tp_mean, Tp_mid=midp("Tp"),
        Tp_max=max(p["Tp"] for p in prof),
        Tf_mid=midp("Tf"), Ts_mid=midp("Ts"), Tr_mid=midp("Tr"),
        Tair_mid=midp("Tair"), T_heater=T_h, T_stack_exit=T_stack_exit,
        Q_rad_risers=th["Q_rad_risers"], Q_conv_risers=th["Q_conv_risers"],
        Q_plate_conv=th["Q_plate_conv"], Q_plate_total=th["Q_plate_total"],
        prof=prof, Re_mid=midp("Re"), h_i_mid=midp("h_i"),
        qf_rad_mid=midp("q_face_rad", 0), qs_rad_mid=midp("q_face_rad", 1),
        qr_rad_mid=midp("q_face_rad", 2),
        qf_conv_mid=midp("q_face_conv", 0), qs_conv_mid=midp("q_face_conv", 1),
        qr_conv_mid=midp("q_face_conv", 2),
    )
    if verbose:
        _print(out)
    return out


def _print(o):
    C = 273.15
    print(f"m_dot        = {o['m_dot']:.3f} kg/s ({o['m_dot']*60:.1f} kg/min)")
    print(f"T_in/out     = {o['T_in']-C:.1f} / {o['T_out']-C:.1f} C   "
          f"dT = {o['dT']:.1f} K")
    print(f"T_cav        = {o['T_cav']-C:.1f} C")
    print(f"plate mean/mid/max = {o['Tp_mean']-C:.0f} / {o['Tp_mid']-C:.0f} / "
          f"{o['Tp_max']-C:.0f} C ; heater sheet ~{o['T_heater']-C:.0f} C")
    print(f"riser7 z=3.5m: front {o['Tf_mid']-C:.1f} / side {o['Ts_mid']-C:.1f}"
          f" / rear {o['Tr_mid']-C:.1f} C ; air {o['Tair_mid']-C:.1f} C")
    print(f"Q into air   = {o['Q_removed']/1e3:.1f} kW | heater-back loss "
          f"{o['Q_back']/1e3:.1f} kW | cavity-wall loss {o['Q_wall']/1e3:.1f} kW")
    print(f"risers: radiation {o['Q_rad_risers']/1e3:.1f} kW, ext convection "
          f"{o['Q_conv_risers']/1e3:.1f} kW | plate convection "
          f"{o['Q_plate_conv']/1e3:.1f} kW")
    frad = o["Q_rad_risers"] / (o["Q_rad_risers"] + o["Q_conv_risers"])
    print(f"radiative fraction of riser heat pickup = {frad:.2f}")
    print(f"Re_mid = {o['Re_mid']:.0f}, h_int mid = {o['h_i_mid']:.1f} W/m2K, "
          f"stack exit {o['T_stack_exit']-C:.1f} C")


if __name__ == "__main__":
    print("=== Case 1: baseline, 82 kWe, outdoor 2 C, building 20 C ===")
    solve_steady(P_elec=82e3, T_outdoor=275.15, T_bldg=293.15, verbose=True)

#!/usr/bin/env python3
"""
RCCS half-scale air-cooled natural-circulation test facility — first-principles model.

Predicts (Case 1 baseline, Case 2 accident transient, Case 3 weather sensitivity):
  - loop natural-circulation air mass flow rate
  - riser air temperature rise
  - riser duct wall temperature (Riser 7, z=3500 mm, hot/front face)
  - heated-plate (mock vessel) front temperature
  - radiation/convection split of heat removal at the risers
  - accident-case peak temperatures and boundedness
  - sensitivity to outdoor air temperature and wind

Method:
  * 1-D loop momentum/energy balance (chimney draft vs. friction/form losses)
    - friction: Petukhov f=(0.79 ln Re - 1.64)^-2 ; K-factors from Idelchik/Crane
  * internal forced convection: Gnielinski correlation (Incropera & DeWitt, Ch. 8)
  * cavity: gray-diffuse radiosity enclosure (2-D crossed-strings view factors, Modest)
    plate / riser-front-faces / inter-duct slot openings / adiabatic side walls
  * riser duct wall: 1-D circumferential fin conduction (finite differences) with
    internal convection sink and external radiation+natural-convection loads
  * natural convection on tall vertical surfaces: Churchill & Chu (1975)
  * accident: quasi-steady removal map R(T_plate) + lumped structural heat capacity ODE

All units SI unless noted. Pure standard-library Python.
"""

import math, json

SIGMA = 5.670e-8
G_GRAV = 9.81
P_ATM = 101325.0
R_AIR = 287.05

# ----------------------------------------------------------------------------
# Air properties, 1 atm  (Incropera & DeWitt, Fund. of Heat & Mass Transfer,
# 6th ed., Table A.4). Linear interpolation; rho from ideal gas.
# ----------------------------------------------------------------------------
_T   = [250, 300, 350, 400, 450, 500, 550, 600, 700]
_CP  = [1006, 1007, 1009, 1014, 1021, 1030, 1040, 1051, 1075]
_MU  = [159.6e-7, 184.6e-7, 208.2e-7, 230.1e-7, 250.7e-7, 270.1e-7,
        288.4e-7, 305.8e-7, 338.8e-7]
_K   = [22.3e-3, 26.3e-3, 30.0e-3, 33.8e-3, 37.3e-3, 40.7e-3,
        43.9e-3, 46.9e-3, 52.4e-3]
_PR  = [0.720, 0.707, 0.700, 0.690, 0.686, 0.684, 0.683, 0.685, 0.695]

def _interp(T, xs, ys):
    T = min(max(T, xs[0]), xs[-1])
    for i in range(len(xs) - 1):
        if T <= xs[i + 1]:
            w = (T - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + w * (ys[i + 1] - ys[i])
    return ys[-1]

def rho_air(T): return P_ATM / (R_AIR * T)
def cp_air(T):  return _interp(T, _T, _CP)
def mu_air(T):  return _interp(T, _T, _MU)
def k_air(T):   return _interp(T, _T, _K)
def pr_air(T):  return _interp(T, _T, _PR)

# ----------------------------------------------------------------------------
# Geometry (from inputs/01_facility_geometry.md)
# ----------------------------------------------------------------------------
N_RISERS   = 12
W_OUT      = 0.0508          # riser narrow (front/rear) outer face, 2 in
D_OUT      = 0.2540          # riser wide (side) outer face, 10 in
T_WALL     = 0.188 * 0.0254  # 4.775 mm
W_IN       = W_OUT - 2 * T_WALL   # 0.04125 m
D_IN       = D_OUT - 2 * T_WALL   # 0.24445 m
A_FLOW_1   = W_IN * D_IN          # 0.010083 m2 per duct
A_FLOW     = N_RISERS * A_FLOW_1  # 0.1210 m2 total
P_IN_1     = 2 * (W_IN + D_IN)    # inner perimeter per duct
DH         = 4 * A_FLOW_1 / P_IN_1  # 0.0706 m
L_RISER    = 7.49            # total riser length (295 in)
L_HEAT     = 6.82            # heated riser length (scaling value)
PITCH      = 1.3208 / N_RISERS    # 52 in / 12 = 0.11007 m
W_GAP      = PITCH - W_OUT        # opening between ducts, 0.0593 m

CAV_W      = 1.3208          # cavity width (52 in)
CAV_GAP    = 0.7066          # plate to riser front face
CAV_H      = 6.7             # cavity height
A_PLATE    = CAV_W * L_HEAT  # 9.01 m2 radiating plate area (envelope basis)

A_DC       = math.pi / 4 * 0.61 ** 2   # downcomer area, 24-in duct
A_CHIM     = 0.584                     # both chimney stacks (given 0.58)
D_CHIM     = 0.61
L_CHIM_EQ  = (826 + 470) * 0.0254      # equivalent friction length per stack, 32.9 m
Z_R1       = 1.1             # elevation, bottom of heated riser section (m)
Z_R2       = Z_R1 + 6.91     # top of heated section
Z_DISCH    = 19.6            # chimney discharge elevation above grade (baseline)

EPS_PLATE  = 0.785           # measured 0.78-0.79
EPS_RISER  = 0.79            # ASSUMED: oxidized structural steel (not reported)
EPS_WALLS  = 0.85            # insulation board faces (assumed; adiabatic so weak)
K_STEEL    = 50.0

# insulated cavity walls (N/S/W): 6 in SuperIsol
U_WALL     = 1.0 / (0.152 / 0.075 + 1.0 / 8.0)     # cond + outside film ~0.46 W/m2K
A_WALL     = 2 * (CAV_H * (CAV_GAP + D_OUT)) + CAV_H * CAV_W   # ~21.7 m2

# Master energy bookkeeping: inputs state 82 kWe electric "corresponds to" the
# scaled 1.5 MWt peak duty = 56.07 kWt removed by the RCCS  =>  parasitic loss
# fraction f_loss = 1 - 56.07/82 = 0.316. This is the single most uncertain input.
F_LOSS     = 0.316

# ----------------------------------------------------------------------------
# Loop hydraulics: buoyant draft vs. losses
# ----------------------------------------------------------------------------
def friction_factor(Re):
    if Re < 2300:
        return 64.0 / max(Re, 1.0)
    return (0.79 * math.log(Re) - 1.64) ** -2          # Petukhov (smooth)

def loop_state(mdot, Q_air, T_in, T_amb, dp_wind, z_disch=Z_DISCH):
    """Return (residual = drive - losses, diagnostics dict)."""
    # outlet temperature (cp at mean T, iterated)
    T_out = T_in + 60.0
    for _ in range(6):
        cp = cp_air(0.5 * (T_in + T_out))
        T_out = T_in + Q_air / (mdot * cp)
    dT = T_out - T_in
    T_m = 0.5 * (T_in + T_out)

    rho_in, rho_out, rho_amb = rho_air(T_in), rho_air(T_out), rho_air(T_amb)
    # density-weighted column in the riser (T linear in z)
    rho_riser = (P_ATM / (R_AIR * dT)) * math.log(T_out / T_in) if dT > 0.05 else rho_in
    T_ch = T_out - 3.0                                  # small chimney loss (assumed)
    rho_ch = rho_air(T_ch)

    drive = G_GRAV * (rho_amb * z_disch
                      - (rho_in * Z_R1
                         + rho_riser * (Z_R2 - Z_R1)
                         + rho_ch * (z_disch - Z_R2))) + dp_wind

    # ---- losses ----
    # downcomer (T_in): entrance 0.5 + flow conditioner 2.0 + elbow 0.3 + friction
    V_dc = mdot / (rho_in * A_DC)
    Re_dc = rho_in * V_dc * 0.61 / mu_air(T_in)
    dp_dc = (2.8 + friction_factor(max(Re_dc, 2500)) * 4.69 / 0.61) \
            * 0.5 * rho_in * V_dc ** 2
    dp_exp = 1.0 * 0.5 * rho_in * V_dc ** 2             # Borda into inlet plenum

    G = mdot / A_FLOW
    V_r_in, V_r_out = G / rho_in, G / rho_out
    V_r_m = G / rho_riser
    Re_r = G * DH / mu_air(T_m)
    f_r = friction_factor(Re_r)
    dp_riser = (0.7 * 0.5 * rho_in * V_r_in ** 2                 # sharp entry + turn
                + f_r * (L_RISER / DH) * 0.5 * rho_riser * V_r_m ** 2
                + 1.0 * 0.5 * rho_out * V_r_out ** 2             # exit into plenum
                + G ** 2 * (1 / rho_out - 1 / rho_in))           # acceleration

    V_ch = mdot / (rho_ch * A_CHIM)
    Re_ch = rho_ch * V_ch * D_CHIM / mu_air(T_ch)
    dp_chim = ((0.5 + 0.9 + friction_factor(max(Re_ch, 2500)) * L_CHIM_EQ / D_CHIM)
               * 0.5 * rho_ch * V_ch ** 2                        # contr + dampers + fric
               + 1.0 * 0.5 * rho_ch * V_ch ** 2)                 # discharge KE

    losses = dp_dc + dp_exp + dp_riser + dp_chim
    diag = dict(T_out=T_out, dT=dT, T_m=T_m, Re_riser=Re_r, V_riser=V_r_m,
                drive_Pa=drive - dp_wind, wind_Pa=dp_wind, losses_Pa=losses,
                dp_downcomer=dp_dc + dp_exp, dp_riser=dp_riser, dp_chimney=dp_chim)
    return drive - losses, diag

def solve_loop(Q_air, T_in=293.15, T_amb=275.15, dp_wind=0.0, z_disch=Z_DISCH):
    lo, hi = 0.02, 8.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        r, _ = loop_state(mid, Q_air, T_in, T_amb, dp_wind, z_disch)
        if r > 0:
            lo = mid
        else:
            hi = mid
    mdot = 0.5 * (lo + hi)
    _, d = loop_state(mdot, Q_air, T_in, T_amb, dp_wind, z_disch)
    d["mdot"] = mdot
    # internal convection coefficient, Gnielinski (props at mean gas T)
    T_m = d["T_m"]
    Re = d["Re_riser"]; Pr = pr_air(T_m); f = friction_factor(Re)
    Nu = (f / 8) * (Re - 1000) * Pr / (1 + 12.7 * math.sqrt(f / 8) * (Pr ** (2 / 3) - 1))
    d["h_i"] = Nu * k_air(T_m) / DH
    d["Nu"] = Nu
    return d

# ----------------------------------------------------------------------------
# Natural convection, tall vertical surface — Churchill & Chu (1975)
# ----------------------------------------------------------------------------
def h_nat(T_s, T_f, L=CAV_H):
    dT = abs(T_s - T_f)
    if dT < 0.1:
        return 1.0
    Tf = 0.5 * (T_s + T_f)
    nu = mu_air(Tf) / rho_air(Tf)
    alpha = k_air(Tf) / (rho_air(Tf) * cp_air(Tf))
    Ra = G_GRAV * (1 / Tf) * dT * L ** 3 / (nu * alpha)
    Pr = pr_air(Tf)
    Nu = (0.825 + 0.387 * Ra ** (1 / 6)
          / (1 + (0.492 / Pr) ** (9 / 16)) ** (8 / 27)) ** 2
    return Nu * k_air(Tf) / L

# ----------------------------------------------------------------------------
# Radiosity enclosure at the cavity cross-section (2-D, per metre of height)
# Surfaces: P plate | F riser front faces | O slot openings | W adiabatic walls
# View factors: crossed strings for opposed parallel strips (Modest, Rad. HT).
# ----------------------------------------------------------------------------
A2 = dict(P=CAV_W, F=N_RISERS * W_OUT, O=N_RISERS * W_GAP, W=2 * CAV_GAP)
_cw = CAV_GAP / CAV_W
F_P_BANK = math.sqrt(1 + _cw ** 2) - _cw          # 0.599
VF = {}
VF[('P', 'F')] = F_P_BANK * A2['F'] / (A2['F'] + A2['O'])
VF[('P', 'O')] = F_P_BANK * A2['O'] / (A2['F'] + A2['O'])
VF[('P', 'W')] = 1 - F_P_BANK
VF[('F', 'P')] = A2['P'] * VF[('P', 'F')] / A2['F']
VF[('F', 'O')] = 0.0
VF[('F', 'W')] = 1 - VF[('F', 'P')]
VF[('O', 'P')] = A2['P'] * VF[('P', 'O')] / A2['O']
VF[('O', 'F')] = 0.0
VF[('O', 'W')] = 1 - VF[('O', 'P')]
VF[('W', 'P')] = A2['P'] * VF[('P', 'W')] / A2['W']
VF[('W', 'F')] = A2['F'] * VF[('F', 'W')] / A2['W']
VF[('W', 'O')] = A2['O'] * VF[('O', 'W')] / A2['W']
VF[('W', 'W')] = 1 - VF[('W', 'P')] - VF[('W', 'F')] - VF[('W', 'O')]

EPS2 = dict(P=EPS_PLATE, F=EPS_RISER, O=0.97, W=EPS_WALLS)
# slot opening effective emissivity ~0.97: cavity effect,
# eps_eff = eps/(eps + (1-eps)*A_open/A_slot_walls) with A_open/A_walls ~ 0.10

def gauss_solve(M, b):
    n = len(b)
    A = [row[:] + [b[i]] for i, row in enumerate(M)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        A[c], A[p] = A[p], A[c]
        for r in range(c + 1, n):
            f = A[r][c] / A[c][c]
            for k in range(c, n + 1):
                A[r][k] -= f * A[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (A[r][n] - sum(A[r][k] * x[k] for k in range(r + 1, n))) / A[r][r]
    return x

def radiosity(T_P, T_F, T_O):
    """Returns net radiative fluxes: q_in on F (W/m2), Q_in on O (W per m height,
    whole row), q_out of plate (W/m2)."""
    names = ['P', 'F', 'O', 'W']
    Eb = {'P': SIGMA * T_P ** 4, 'F': SIGMA * T_F ** 4, 'O': SIGMA * T_O ** 4}
    M, b = [], []
    for i in names:
        row = []
        for j in names:
            if i == 'W':           # adiabatic (re-radiating): J_W = sum F_Wj J_j
                v = (1.0 if j == 'W' else 0.0) - VF[('W', j)] if ('W', j) in VF else 0.0
                if j == 'W':
                    v = 1.0 - VF[('W', 'W')]
                else:
                    v = -VF[('W', j)]
                row.append(v)
            else:
                v = (1.0 if i == j else 0.0)
                if j != i or True:
                    v -= (1 - EPS2[i]) * VF[(i, j)] if (i, j) in VF else 0.0
                row.append(v)
        M.append(row)
        b.append(0.0 if i == 'W' else EPS2[i] * Eb[i])
    J = dict(zip(names, gauss_solve(M, b)))
    def q_leave(i):
        return EPS2[i] / (1 - EPS2[i]) * (Eb[i] - J[i])
    q_in_F = -q_leave('F')                       # W/m2, net absorbed by front faces
    Q_in_O = -q_leave('O') * A2['O']             # W per m height, whole row
    q_out_P = q_leave('P')                       # W/m2, net leaving plate
    return q_in_F, Q_in_O, q_out_P

# ----------------------------------------------------------------------------
# Riser duct wall: 1-D circumferential conduction (half perimeter, symmetric)
# ----------------------------------------------------------------------------
N_FD = 81
S_HALF = 0.5 * W_OUT + D_OUT + 0.5 * W_OUT * 0.0 + 0.5 * W_OUT  # front half + side + rear half
S_HALF = 0.5 * W_OUT + D_OUT + 0.5 * W_OUT                       # 0.3048 m
DS = S_HALF / (N_FD - 1)
S_POS = [i * DS for i in range(N_FD)]
REGION = ['front' if s < 0.5 * W_OUT else ('side' if s < 0.5 * W_OUT + D_OUT else 'rear')
          for s in S_POS]

def thomas(a, b, c, d):
    n = len(d)
    cp = [0.0] * n; dp = [0.0] * n
    cp[0] = c[0] / b[0]; dp[0] = d[0] / b[0]
    for i in range(1, n):
        m = b[i] - a[i] * cp[i - 1]
        cp[i] = c[i] / m
        dp[i] = (d[i] - a[i] * dp[i - 1]) / m
    x = [0.0] * n
    x[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x

def riser_fd(q_front, q_side, h_ext, T_c, h_i, T_air):
    """Solve wall temperature profile T(s). q_* = imposed radiative fluxes (W/m2),
    h_ext = dict of external convective h per region, T_c cavity air temp."""
    kt = K_STEEL * T_WALL
    a = [0.0] * N_FD; b = [0.0] * N_FD; c = [0.0] * N_FD; d = [0.0] * N_FD
    for i in range(N_FD):
        reg = REGION[i]
        he = h_ext[reg]
        qr = q_front if reg == 'front' else (q_side if reg == 'side' else 0.0)
        b[i] = -2 * kt / DS ** 2 - (h_i + he)
        a[i] = kt / DS ** 2
        c[i] = kt / DS ** 2
        d[i] = -(h_i * T_air + he * T_c + qr)
    # symmetry (Neumann) ends
    c[0] = 2 * kt / DS ** 2; a[0] = 0.0
    a[-1] = 2 * kt / DS ** 2; c[-1] = 0.0
    return thomas(a, b, c, d)

def trap(vals, ds):
    return ds * (0.5 * vals[0] + sum(vals[1:-1]) + 0.5 * vals[-1])

# ----------------------------------------------------------------------------
# Coupled cavity solution: find plate temperature that delivers Q_air to risers
# ----------------------------------------------------------------------------
def cavity_solve(Q_target, T_air_mid, h_i, T_room=293.15, verbose=False):
    def q_riser_of_Tp(T_P):
        T_prof = [T_air_mid + 60.0] * N_FD
        T_c = T_air_mid + 80.0
        T_F = T_prof[0]; T_O = T_prof[N_FD // 2]
        out = {}
        for it in range(120):
            q_in_F, Q_in_O, q_out_P = radiosity(T_P, T_F, T_O)
            q_side = Q_in_O / (N_RISERS * 2 * D_OUT)     # spread on slot side faces
            h_ext = dict(front=h_nat(T_c, T_prof[0]),
                         side=0.7 * h_nat(T_c, T_O),     # confined slot: 0.7 factor
                         rear=0.7 * h_nat(T_c, T_prof[-1]))
            T_new = riser_fd(q_in_F, q_side, h_ext, T_c, h_i, T_air_mid)
            T_prof = [0.5 * o + 0.5 * n for o, n in zip(T_prof, T_new)]
            # face means
            fr = [T_prof[i] for i in range(N_FD) if REGION[i] == 'front']
            sd = [T_prof[i] for i in range(N_FD) if REGION[i] == 'side']
            rr = [T_prof[i] for i in range(N_FD) if REGION[i] == 'rear']
            T_F = 0.5 * T_F + 0.5 * sum(fr) / len(fr)
            T_O = 0.5 * T_O + 0.5 * sum(sd) / len(sd)
            # cavity air balance
            h_p = h_nat(T_P, T_c)
            A_fr = N_RISERS * W_OUT * L_HEAT
            A_sd = N_RISERS * 2 * D_OUT * L_HEAT
            A_rr = A_fr
            num = (h_p * A_PLATE * T_P + h_ext['front'] * A_fr * T_F
                   + h_ext['side'] * A_sd * T_O + h_ext['rear'] * A_rr * T_prof[-1]
                   + U_WALL * A_WALL * T_room)
            den = (h_p * A_PLATE + h_ext['front'] * A_fr + h_ext['side'] * A_sd
                   + h_ext['rear'] * A_rr + U_WALL * A_WALL)
            T_c = 0.5 * T_c + 0.5 * num / den
        # heat into riser air (both symmetric halves, 12 ducts, heated length)
        q_conv_in = [h_i * (T - T_air_mid) for T in T_prof]
        Q_riser = trap(q_conv_in, DS) * 2 * N_RISERS * L_HEAT
        # radiative / convective split at riser outer surfaces
        Q_rad_abs = (q_in_F * A2['F'] + Q_in_O) * L_HEAT
        Q_conv_ext = Q_riser - Q_rad_abs
        Q_plate_rad = q_out_P * A_PLATE
        Q_plate_conv = h_p * A_PLATE * (T_P - T_c)
        Q_wall_loss = U_WALL * A_WALL * (T_c - T_room)
        out.update(T_prof=T_prof, T_c=T_c, T_front=T_prof[0], T_F=T_F,
                   T_side=T_O, T_rear=T_prof[-1], Q_riser=Q_riser,
                   Q_rad_abs=Q_rad_abs, Q_conv_ext=Q_conv_ext,
                   f_rad=Q_rad_abs / Q_riser if Q_riser else 0.0,
                   Q_plate_rad=Q_plate_rad, Q_plate_conv=Q_plate_conv,
                   Q_wall_loss=Q_wall_loss, h_p=h_p, h_ext=h_ext,
                   q_in_F=q_in_F, Q_in_O=Q_in_O)
        return Q_riser, out

    lo, hi = T_air_mid + 20.0, 1300.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        Q, out = q_riser_of_Tp(mid)
        if Q < Q_target:
            lo = mid
        else:
            hi = mid
    T_P = 0.5 * (lo + hi)
    Q, out = q_riser_of_Tp(T_P)
    out['T_plate'] = T_P
    if verbose:
        print(f"  cavity: Tp={T_P-273.15:.1f}C  Q_riser={Q/1e3:.2f}kW "
              f"(target {Q_target/1e3:.2f})  f_rad={out['f_rad']:.3f}")
    return out

# ----------------------------------------------------------------------------
# Full steady case
# ----------------------------------------------------------------------------
def steady_case(Q_elec, f_loss=F_LOSS, T_in=293.15, T_amb=275.15,
                dp_wind=0.0, z_disch=Z_DISCH):
    Q_air = (1 - f_loss) * Q_elec
    loop = solve_loop(Q_air, T_in, T_amb, dp_wind, z_disch)
    # local air temperature at instrument mid-plane z=3500mm of 6910mm in-cavity run
    T_air_mid = T_in + (3.5 / 6.91) * loop['dT']
    cav = cavity_solve(Q_air, T_air_mid, loop['h_i'])
    return dict(Q_elec=Q_elec, Q_air=Q_air, loop=loop, cav=cav,
                T_air_mid=T_air_mid)

def summarize(case, label):
    lp, cv = case['loop'], case['cav']
    return dict(
        label=label,
        Q_elec_kW=case['Q_elec'] / 1e3,
        Q_air_kW=case['Q_air'] / 1e3,
        mdot_kgs=round(lp['mdot'], 3),
        mdot_kgmin=round(lp['mdot'] * 60, 1),
        dT_C=round(lp['dT'], 1),
        T_out_C=round(lp['T_out'] - 273.15, 1),
        V_riser_ms=round(lp['V_riser'], 2),
        Re_riser=int(lp['Re_riser']),
        h_i=round(lp['h_i'], 1),
        drive_Pa=round(lp['drive_Pa'], 1),
        riser_wall_hotface_C=round(cv['T_front'] - 273.15, 1),
        riser_wall_side_C=round(cv['T_side'] - 273.15, 1),
        riser_wall_rear_C=round(cv['T_rear'] - 273.15, 1),
        plate_C=round(cv['T_plate'] - 273.15, 1),
        cavity_air_C=round(cv['T_c'] - 273.15, 1),
        rad_fraction=round(cv['f_rad'], 3),
        plate_rad_kW=round(cv['Q_plate_rad'] / 1e3, 1),
        plate_conv_kW=round(cv['Q_plate_conv'] / 1e3, 1),
        wall_loss_kW=round(cv['Q_wall_loss'] / 1e3, 1),
    )

# ----------------------------------------------------------------------------
# Case 2 — accident decay-heat transient
# ----------------------------------------------------------------------------
POLY_C = [466.531039994, 0.078631095079, 0.000170562320568, -1.28449427566e-07,
          5.09424812301e-11, -1.27606140005e-14, 2.04789514471e-18,
          -2.08318254453e-22, 1.29530038954e-26, -4.48601180685e-31]

def p_poly_W(t_min):
    return sum(c * t_min ** n for n, c in enumerate(POLY_C)) * 90.0

def p_shape_W(t_s):
    """Fallback: 26.16 -> 56.07 kW, peak at 84.85 h, gamma-like decline."""
    tp = 84.85 * 3600.0
    x = t_s / tp
    return 26160.0 + (56070.0 - 26160.0) * (x ** 2) * math.exp(2 * (1 - x))

def check_polynomial():
    pts = {}
    ok = True
    for h in [0, 20, 40, 60, 84.85, 100, 120, 150]:
        w = p_poly_W(h * 60)
        pts[h] = w / 1e3
    peak_ok = 50e3 < p_poly_W(84.85 * 60) < 62e3
    start_ok = 20e3 < p_poly_W(0) < 32e3
    tail_ok = 0 < p_poly_W(150 * 60) < p_poly_W(84.85 * 60)
    return pts, (peak_ok and start_ok and tail_ok)

def accident_transient(f_loss=F_LOSS, use_poly=None):
    pts, poly_ok = check_polynomial()
    if use_poly is None:
        use_poly = poly_ok
    P = (lambda t: p_poly_W(t / 60.0)) if use_poly else p_shape_W

    # quasi-steady removal map: T_plate -> Q_air removed (and mdot, dT, wall T)
    grid = [16e3, 22e3, 28e3, 36e3, 44e3, 52e3, 60e3, 70e3, 82e3, 95e3]
    tab = []
    for Qe in grid:
        c = steady_case(Qe, f_loss)
        tab.append((c['cav']['T_plate'], c['Q_air'], c['loop']['mdot'],
                    c['loop']['dT'], c['cav']['T_front']))
    tab.sort()
    def interp_col(Tp, col):
        xs = [r[0] for r in tab]; ys = [r[col] for r in tab]
        if Tp <= xs[0]:
            return ys[0] + (ys[1] - ys[0]) * (Tp - xs[0]) / (xs[1] - xs[0])
        if Tp >= xs[-1]:
            return ys[-1] + (ys[-1] - ys[-2]) * (Tp - xs[-1]) / (xs[-1] - xs[-2])
        for i in range(len(xs) - 1):
            if Tp <= xs[i + 1]:
                w = (Tp - xs[i]) / (xs[i + 1] - xs[i])
                return ys[i] + w * (ys[i + 1] - ys[i])
    # lumped heat capacity: plate (0.85e6) + risers (0.99e6) + heaters/board and
    # near-surface structure (~1.2e6) J/K  (assumption)
    C_EFF = 3.0e6
    # initial condition: steady at P(0)
    Tp = None
    lo, hi = 300.0, 1200.0
    P0 = (1 - f_loss) * P(0.0)
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if interp_col(mid, 1) < P0:
            lo = mid
        else:
            hi = mid
    Tp = 0.5 * (lo + hi)
    dt = 120.0
    t_end = 160 * 3600.0
    t = 0.0
    peak = (Tp, 0.0)
    hist = []
    while t < t_end:
        def f(T, tt):
            return ((1 - f_loss) * P(tt) - interp_col(T, 1)) / C_EFF
        k1 = f(Tp, t)
        k2 = f(Tp + 0.5 * dt * k1, t + 0.5 * dt)
        k3 = f(Tp + 0.5 * dt * k2, t + 0.5 * dt)
        k4 = f(Tp + dt * k3, t + dt)
        Tp += dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        t += dt
        if Tp > peak[0]:
            peak = (Tp, t)
        if int(t) % (4 * 3600) < dt:
            hist.append((t / 3600.0, P(t) / 1e3, Tp - 273.15,
                         interp_col(Tp, 2), interp_col(Tp, 3),
                         interp_col(Tp, 4) - 273.15))
    Tp_pk, t_pk = peak
    res = dict(used_polynomial=use_poly, poly_check_kW=pts,
               peak_plate_C=round(Tp_pk - 273.15, 1),
               peak_time_h=round(t_pk / 3600.0, 1),
               mdot_at_peak_kgs=round(interp_col(Tp_pk, 2), 3),
               dT_at_peak_C=round(interp_col(Tp_pk, 3), 1),
               riser_wall_at_peak_C=round(interp_col(Tp_pk, 4) - 273.15, 1),
               C_eff_JK=C_EFF, history=hist)
    return res

# ----------------------------------------------------------------------------
# Case 3 — weather sensitivity
# ----------------------------------------------------------------------------
def weather_grid(Q_elec=82e3, f_loss=F_LOSS):
    rows = []
    base = steady_case(Q_elec, f_loss, T_amb=275.15)
    m0 = base['loop']['mdot']
    for T_amb_C in [-18, 2, 24]:
        for wind, cp_tip in [(0.0, 0.0), (5.5, -0.3), (11.0, -0.3), (11.0, +0.2)]:
            rho_a = rho_air(273.15 + T_amb_C)
            dp_w = -cp_tip * 0.5 * rho_a * wind ** 2
            c = steady_case(Q_elec, f_loss, T_amb=273.15 + T_amb_C, dp_wind=dp_w)
            rows.append(dict(T_amb_C=T_amb_C, wind_ms=wind, Cp_tip=cp_tip,
                             dp_wind_Pa=round(dp_w, 1),
                             mdot_kgs=round(c['loop']['mdot'], 3),
                             mdot_change_pct=round(100 * (c['loop']['mdot'] / m0 - 1), 1),
                             dT_C=round(c['loop']['dT'], 1),
                             plate_C=round(c['cav']['T_plate'] - 273.15, 1),
                             riser_wall_C=round(c['cav']['T_front'] - 273.15, 1)))
    return rows

# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 76)
    print("CASE 1 — baseline steady state, 82 kWe, natural circulation")
    print("=" * 76)
    base = steady_case(82e3)
    s1 = summarize(base, 'Case 1 baseline (f_loss=0.316)')
    for k, v in s1.items():
        print(f"  {k:26s} {v}")
    # energy closure check
    cv = base['cav']
    print(f"  [check] plate out (rad+conv) = "
          f"{(cv['Q_plate_rad']+cv['Q_plate_conv'])/1e3:.1f} kW "
          f"vs riser pickup + wall loss = "
          f"{(cv['Q_riser']+cv['Q_wall_loss'])/1e3:.1f} kW")

    print("\nSensitivity to parasitic-loss fraction:")
    sens = {}
    for fl in [0.15, 0.316, 0.40]:
        c = steady_case(82e3, f_loss=fl)
        sens[fl] = summarize(c, f'f_loss={fl}')
        print(f"  f_loss={fl:5.3f}: mdot={sens[fl]['mdot_kgs']:.3f} kg/s, "
              f"dT={sens[fl]['dT_C']:.1f} C, plate={sens[fl]['plate_C']:.0f} C, "
              f"riser wall={sens[fl]['riser_wall_hotface_C']:.0f} C, "
              f"f_rad={sens[fl]['rad_fraction']:.2f}")

    print("\n" + "=" * 76)
    print("CASE 2 — accident decay-heat transient")
    print("=" * 76)
    acc = accident_transient()
    print(f"  polynomial sanity (kW at h): "
          f"{ {k: round(v,1) for k,v in acc['poly_check_kW'].items()} }")
    print(f"  used polynomial: {acc['used_polynomial']}")
    print(f"  peak plate {acc['peak_plate_C']} C at t={acc['peak_time_h']} h; "
          f"mdot at peak {acc['mdot_at_peak_kgs']} kg/s; "
          f"riser wall at peak {acc['riser_wall_at_peak_C']} C")
    print("  t(h)   P(kW)  Tplate(C)  mdot   dT(C)  wall(C)")
    for r in acc['history'][:40]:
        print("  %6.1f %6.1f  %8.1f  %5.3f  %5.1f  %6.1f" % r)

    print("\n" + "=" * 76)
    print("CASE 3 — weather sensitivity (82 kWe)")
    print("=" * 76)
    wx = weather_grid()
    print("  Tamb(C) wind(m/s) Cp    dpw(Pa)  mdot(kg/s)  d(mdot)%  dT(C)  plate(C)")
    for r in wx:
        print("  %6.0f  %6.1f  %5.2f  %7.1f  %9.3f  %8.1f  %5.1f  %7.1f"
              % (r['T_amb_C'], r['wind_ms'], r['Cp_tip'], r['dp_wind_Pa'],
                 r['mdot_kgs'], r['mdot_change_pct'], r['dT_C'], r['plate_C']))

    # -------- results.json --------
    weather_note = (
        "Colder outdoor air strengthens the chimney draft (denser ambient column): "
        f"mdot {wx[0]['mdot_change_pct']:+.0f}% at -18 C and "
        f"{wx[8]['mdot_change_pct']:+.0f}% at +24 C versus the +2 C baseline, with "
        "riser dT and all metal temperatures moving opposite to flow. Wind of ~11 m/s "
        "carries a dynamic pressure (~75 Pa) comparable to the whole buoyant head "
        "(~60 Pa): with stack-tip suction (Cp ~ -0.3) it raises flow "
        f"{wx[6]['mdot_change_pct']:+.0f}%; adverse stack pressurization (Cp ~ +0.2) "
        f"cuts it {wx[7]['mdot_change_pct']:+.0f}% and is the main risk of degraded or "
        "oscillatory performance. Heat-removal capability changes little because "
        "radiation dominates: plate temperature moves only ~-5/+12 C across the whole "
        "-18..+24 C, 0..11 m/s envelope.")

    results = dict(
        mdot_kgs=s1['mdot_kgs'],
        dT_C=s1['dT_C'],
        riser_wall_C=s1['riser_wall_hotface_C'],
        plate_C=s1['plate_C'],
        rad_fraction=s1['rad_fraction'],
        accident_peak_plate_C=acc['peak_plate_C'],
        accident_bounded=bool(acc['peak_plate_C'] < 425.0),
        weather_flow_change_note=weather_note,
        detail=dict(case1=s1,
                    f_loss_sensitivity={str(k): v for k, v in sens.items()},
                    accident={k: v for k, v in acc.items() if k != 'history'},
                    weather=wx),
    )
    with open('/Users/charlesazam/eng-bench/runs/run_fableA/results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nresults.json written.")

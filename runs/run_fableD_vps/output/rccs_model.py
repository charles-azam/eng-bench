"""
Physics-based steady-state model of a 1/2-axial-scale, air-cooled RCCS test facility.

Built ONLY from the geometry / materials / boundary conditions in ../inputs/ plus
first-principles heat transfer and standard cited correlations. No facility test data used.

Model summary
-------------
Natural-circulation loop: building air -> 24" downcomer -> inlet plenum -> 12 rectangular
steel riser ducts (heated over the 6.7 m cavity height) -> outlet plenum -> two 24" insulated
chimney stacks discharging outdoors at 19.6 m.

Cavity heat transfer, per axial segment (10 segments matching the heater zones):
  surfaces: P = heated plate, F = riser front (narrow) faces, S = riser side (wide) faces,
            R = riser rear (narrow) faces, W = insulated wall behind the risers.
  - grey-diffuse radiosity network (view factors from 2-D crossed-strings on the unit cell,
    reciprocity enforced),
  - natural convection plate -> cavity air -> duct faces / walls (Churchill-Chu turbulent
    vertical plate; Incropera & DeWitt, Fundamentals of Heat and Mass Transfer, Eq. 9.26),
  - conduction around the duct perimeter (fin links between face nodes),
  - grey radiosity exchange between the duct's internal faces,
  - forced convection duct wall -> air: Gnielinski (Int. Chem. Eng. 16 (1976) 359) with a
    thermal-entrance enhancement (Kays, Crawford & Weigand, Convective Heat & Mass Transfer).
Heater array: radiates to the plate back across a gap (grey two-surface exchange) and loses
heat through 2" Duraboard to the building (parasitic).

Loop momentum: sum(rho*g*dz) around the loop against the outdoor-air column, balanced against
friction (Churchill 1977 friction factor, commercial-steel roughness) + form losses
(Idelchik, Handbook of Hydraulic Resistance, typical K values) + acceleration.

Air properties: Incropera & DeWitt Table A.4 (interpolated), ideal-gas density at 101325 Pa.
"""

import numpy as np
from scipy.optimize import brentq, fsolve

SIGMA = 5.670e-8
G_GRAV = 9.81
P_ATM = 101325.0
R_AIR = 287.05
IN = 0.0254

# ----------------------------------------------------------------------------- geometry
GEO = dict(
    n_ducts=12,
    duct_out_w=10 * IN,          # wide face (faces neighbours)
    duct_out_n=2 * IN,           # narrow face (front faces the plate)
    t_wall=0.188 * IN,
    duct_len=295 * IN,           # total riser length
    L_heated=6.70,               # heated cavity height (22 ft)
    z_riser_bot=-7 * IN,         # riser bottom lip below cavity floor (z=0 heated bottom)
    cav_width=52 * IN,           # 1.3208 m
    cav_depth=0.7066,            # plate to riser front face (baseline)
    pitch=52 * IN / 12,          # duct centre-to-centre across the width (~4.33 in)
    A_plate=10.18,               # as-built heated-plate area, m^2
    t_plate=1 * IN,
    # flow path
    D_dc=0.61, L_dc=184.5 * IN,          # inlet downcomer
    z_intake=3.5,                        # ASSUMPTION: downcomer intake elevation
    A_chim=0.584, D_chim=0.61,           # both stacks
    L_chim_vert_eq=826 * IN, L_chim_horz_eq=470 * IN,   # equivalent lengths (per system)
    z_port=8.34,                         # chimney port centreline (56.5" above plenum floor)
    z_discharge=19.6,
    z_chim_top=19.6,
    # insulation
    t_sup=0.152, t_dur=2 * IN, t_wrap=3 * IN,
)
GEO['duct_in_w'] = GEO['duct_out_w'] - 2 * GEO['t_wall']   # 9.624 in
GEO['duct_in_n'] = GEO['duct_out_n'] - 2 * GEO['t_wall']   # 1.624 in
GEO['A_flow_1'] = GEO['duct_in_w'] * GEO['duct_in_n']      # 0.01008 m^2
GEO['A_flow'] = GEO['n_ducts'] * GEO['A_flow_1']
GEO['P_wet_1'] = 2 * (GEO['duct_in_w'] + GEO['duct_in_n'])
GEO['Dh'] = 4 * GEO['A_flow_1'] / GEO['P_wet_1']           # 0.0706 m
GEO['z_riser_top'] = GEO['z_riser_bot'] + GEO['duct_len']  # 7.315 m

NSEG = 10

# ----------------------------------------------------------------------------- air properties
_T = np.array([200, 250, 300, 350, 400, 450, 500, 550, 600, 700, 800, 900, 1000.])
_CP = np.array([1007, 1006, 1007, 1009, 1014, 1021, 1030, 1040, 1051, 1075, 1099, 1121, 1141.])
_MU = np.array([13.25, 15.96, 18.46, 20.82, 23.01, 25.07, 27.01, 28.84, 30.58,
                33.88, 36.98, 39.81, 42.44]) * 1e-6
_K = np.array([18.1, 22.3, 26.3, 30.0, 33.8, 37.3, 40.7, 43.9, 46.9, 52.4, 57.3,
               62.0, 66.7]) * 1e-3

def air(T):
    """Air properties at temperature T [K], 1 atm. Incropera Table A.4."""
    T = np.clip(T, 200, 1000)
    rho = P_ATM / (R_AIR * T)
    cp = np.interp(T, _T, _CP)
    mu = np.interp(T, _T, _MU)
    k = np.interp(T, _T, _K)
    return rho, cp, mu, k, cp * mu / k

def rho_air(T):
    return P_ATM / (R_AIR * T)

# insulation conductivities W/mK vs K (from inputs, converted)
def k_superisol(T):
    return np.interp(T, [477, 672, 866], [0.060, 0.080, 0.100])

def k_duraboard(T):
    return np.interp(T, [477, 811], [0.0793, 0.1221])

def k_enerwrap(T):
    return np.interp(T, [366, 477, 589], [0.0433, 0.0606, 0.0851])

# ----------------------------------------------------------------------------- correlations
def f_churchill(Re, rough_rel):
    """Churchill (1977) friction factor, all regimes."""
    Re = max(Re, 1.0)
    A = (2.457 * np.log(1.0 / ((7.0 / Re) ** 0.9 + 0.27 * rough_rel))) ** 16
    B = (37530.0 / Re) ** 16
    return 8.0 * ((8.0 / Re) ** 12 + 1.0 / (A + B) ** 1.5) ** (1.0 / 12.0)

def nu_gnielinski(Re, Pr):
    if Re < 2300:
        return 4.36
    Re = min(Re, 5e6)
    f = (0.790 * np.log(Re) - 1.64) ** -2
    return (f / 8) * (Re - 1000) * Pr / (1 + 12.7 * np.sqrt(f / 8) * (Pr ** (2 / 3) - 1))

def h_internal(Re, Pr, k, Dh, x):
    """Local internal h with thermal-entrance enhancement ~ (1 + (x/D)^-0.9)."""
    nu = nu_gnielinski(Re, Pr)
    xD = max(x / Dh, 1.0)
    return nu * (1 + xD ** -0.9) * k / Dh

def h_natural_vertical(Ts, Tf, L):
    """Churchill-Chu vertical plate (Incropera Eq. 9.26), film properties."""
    Tfilm = 0.5 * (Ts + Tf)
    rho, cp, mu, k, Pr = air(Tfilm)
    beta = 1.0 / Tfilm
    dT = abs(Ts - Tf) + 1e-6
    Ra = G_GRAV * beta * dT * L ** 3 * rho ** 2 * cp / (mu * k)
    Nu = (0.825 + 0.387 * Ra ** (1 / 6) /
          (1 + (0.492 / Pr) ** (9 / 16)) ** (8 / 27)) ** 2
    return Nu * k / L

# ----------------------------------------------------------------------------- view factors
def cavity_viewfactors():
    """5-surface [P,F,S,R,W] per-segment view-factor matrix.

    2-D crossed-strings estimates on the periodic unit cell (pitch 110 mm, gap 59.3 mm,
    duct depth 254 mm, cavity depth 707 mm >> pitch so radiation arriving at the riser
    plane is treated as uniformly distributed). Reciprocity + row sums enforced by
    iterative proportional fitting.
    """
    g = GEO
    Lseg = g['L_heated'] / NSEG
    A = np.array([
        g['cav_width'] * Lseg,                                  # P
        g['n_ducts'] * g['duct_out_n'] * Lseg,                  # F
        g['n_ducts'] * 2 * g['duct_out_w'] * Lseg,              # S (both sides)
        g['n_ducts'] * g['duct_out_n'] * Lseg,                  # R
        g['cav_width'] * Lseg,                                  # W
    ])
    w_f = g['n_ducts'] * g['duct_out_n'] / g['cav_width']       # 0.4615 fronts
    w_g = 1 - w_f                                               # gap openings
    # gap channel: strips w=59.3mm separated by depth 254mm -> F(open->rear) by crossed strings
    wgap = g['pitch'] - g['duct_out_n']
    d = g['duct_out_w']
    x = d / wgap
    F_open_rear = np.sqrt(1 + x ** 2) - x        # ~0.115
    F_open_side = 1 - F_open_rear
    # rear region: split arriving radiation between W and duct rears by area
    fr_W = A[4] / (A[4] + A[3])
    F = np.zeros((5, 5))
    # from plate
    F[0, 1] = w_f
    F[0, 2] = w_g * F_open_side
    F[0, 4] = w_g * F_open_rear * fr_W
    F[0, 3] = w_g * F_open_rear * (1 - fr_W)
    # from fronts: see the plate (plane-to-plane, depth >> pitch)
    F[1, 0] = 1.0
    # from sides: opposing side across the gap, remainder out the two openings
    xs = wgap / d
    F_ss = np.sqrt(1 + xs ** 2) - xs             # ~0.79
    F[2, 2] = F_ss
    F[2, 0] = (1 - F_ss) / 2                     # out the front opening -> plate
    F[2, 4] = (1 - F_ss) / 2 * fr_W              # out the rear opening
    F[2, 3] = (1 - F_ss) / 2 * (1 - fr_W)
    # from rears: mostly the back wall
    F[3, 0] = F[0, 3] * A[0] / A[3] * 0.0 + 0.04   # small direct return through gaps
    F[3, 2] = 0.30
    F[3, 4] = 1 - F[3, 0] - F[3, 2]
    # from back wall
    F[4, 3] = F[3, 4] * A[3] / A[4]
    F[4, 2] = 0.35
    F[4, 0] = 0.05
    F[4, 4] = 1 - F[4, 3] - F[4, 2] - F[4, 0]     # wall is flat; residual ~ cavity ends, fold in
    # enforce reciprocity & row sums (iterative proportional fitting on A_i F_ij)
    M = F * A[:, None]
    for _ in range(200):
        M = 0.5 * (M + M.T)
        M *= (A / np.maximum(M.sum(1), 1e-12))[:, None]
    F = M / A[:, None]
    return A, F

def duct_internal_viewfactors():
    """Internal 3-surface [front, sides(2), rear] view factors, 2-D crossed strings."""
    g = GEO
    Lseg = g['L_heated'] / NSEG
    w = g['duct_in_n']      # narrow width 41.3 mm
    d = g['duct_in_w']      # depth 244.5 mm
    x = d / w
    F_fr = np.sqrt(1 + x ** 2) - x               # front -> rear, ~0.084
    A = np.array([w, 2 * d, w]) * Lseg * g['n_ducts']
    F = np.zeros((3, 3))
    F[0, 2] = F_fr
    F[0, 1] = 1 - F_fr
    F[2, 0] = F_fr
    F[2, 1] = 1 - F_fr
    F[1, 0] = F[0, 1] * A[0] / A[1]
    F[1, 2] = F[2, 1] * A[2] / A[1]
    xs = w / d
    F[1, 1] = 1 - F[1, 0] - F[1, 2]              # side -> opposite side
    return A, F

def radiosity_net(T, A, F, eps):
    """Grey-diffuse radiosity solve. Returns net heat LEAVING each surface [W]."""
    T = np.asarray(T, float)
    eb = SIGMA * T ** 4
    n = len(T)
    M = np.eye(n) - (1 - eps)[:, None] * F
    J = np.linalg.solve(M, eps * eb)
    q = A * eps / (1 - eps) * (eb - J) if np.all(eps < 1) else None
    # generic (works for eps<1): q_i = A_i (J_i - sum F_ij J_j) also valid
    q = A * (J - F @ J)
    return q

# ----------------------------------------------------------------------------- parameters
PARAMS = dict(
    eps_plate=0.785,       # measured (inputs)
    eps_duct=0.80,         # ASSUMED: oxidized structural steel (Incropera Table A.11: 0.79)
    eps_wall=0.85,         # ASSUMED: board-insulation face
    eps_heater=0.90,       # sandblasted SS backing (inputs)
    eps_plate_back=0.78,
    k_steel=50.0,
    f_edge_loss=0.05,      # ASSUMED: edge/frame/penetration parasitic, fraction of P_elec
    R_ext=0.17,            # outside film resistance on insulation, m^2K/W (h~6)
    K_conditioner=2.0,     # ASSUMED flow-conditioner loss coefficient
    K_dampers=1.0,         # 5 butterfly dampers, open (K~0.2-0.3 each, ~2-3 in series/stack)
    Cp_wind=0.0,           # wind pressure coefficient at stack discharge (negative = suction)
    rough=1.5e-4,          # galvanized/commercial steel roughness, m
)

A_CAV, F_CAV = cavity_viewfactors()
A_INT, F_INT = duct_internal_viewfactors()

# fin conduction links per segment (all 12 ducts), F<->S and S<->R around the perimeter
def fin_conductance():
    g = GEO
    Lseg = g['L_heated'] / NSEG
    path = g['duct_out_n'] / 2 + g['duct_out_w'] / 2     # centroid-to-centroid ~0.152 m
    G1 = PARAMS['k_steel'] * g['t_wall'] * Lseg / path   # one corner path
    return 2 * G1 * g['n_ducts']                          # two corners, 12 ducts

G_FS = fin_conductance()
G_SR = fin_conductance()

# ----------------------------------------------------------------------------- segment solve
def segment_balance(x, q_seg, T_cav, T_gas, h_i, T_bldg, prm):
    """Residuals for one axial segment. x = [T_h, T_P, T_F, T_S, T_R, T_W] in K.
    q_seg: electric power reaching this plate segment (after edge loss) [W]."""
    T_h, T_P, T_F, T_S, T_R, T_W = x
    g = GEO
    Lseg = g['L_heated'] / NSEG
    A_P, A_F, A_S, A_R, A_W = A_CAV
    eps = np.array([prm['eps_plate'], prm['eps_duct'], prm['eps_duct'],
                    prm['eps_duct'], prm['eps_wall']])
    q_rad = radiosity_net([T_P, T_F, T_S, T_R, T_W], A_CAV, F_CAV, eps)  # net leaving

    # cavity natural convection (characteristic length = full cavity height)
    L = g['L_heated']
    h_P = h_natural_vertical(T_P, T_cav, L)
    h_F = h_natural_vertical(T_F, T_cav, L)
    h_S = h_natural_vertical(T_S, T_cav, L) * 0.7   # ASSUMED restriction in 59-mm gaps
    h_R = h_natural_vertical(T_R, T_cav, L) * 0.7
    h_W = h_natural_vertical(T_W, T_cav, L) * 0.7

    # duct internal radiation (net leaving each internal face)
    q_ri = radiosity_net([T_F, T_S, T_R], A_INT, F_INT,
                         np.array([prm['eps_duct']] * 3))

    # internal convective areas
    Ai_F = g['n_ducts'] * g['duct_in_n'] * Lseg
    Ai_S = g['n_ducts'] * 2 * g['duct_in_w'] * Lseg
    Ai_R = Ai_F

    # heater -> plate back (two-surface grey exchange), heater backside loss
    Rr = 1 / prm['eps_heater'] + 1 / prm['eps_plate_back'] - 1
    q_h2p = g['A_plate'] / NSEG * SIGMA * (T_h ** 4 - T_P ** 4) / Rr
    R_back = g['t_dur'] / k_duraboard(T_h) + prm['R_ext']
    q_back = g['A_plate'] / NSEG * (T_h - T_bldg) / R_back

    r = np.zeros(6)
    r[0] = q_seg - q_h2p - q_back
    r[1] = q_h2p - q_rad[0] - h_P * A_P * (T_P - T_cav)
    r[2] = -q_rad[1] + h_F * A_F * (T_cav - T_F) + G_FS * (T_S - T_F) \
        - q_ri[0] - h_i * Ai_F * (T_F - T_gas)
    r[3] = -q_rad[2] + h_S * A_S * (T_cav - T_S) + G_FS * (T_F - T_S) \
        + G_SR * (T_R - T_S) - q_ri[1] - h_i * Ai_S * (T_S - T_gas)
    r[4] = -q_rad[3] + h_R * A_R * (T_cav - T_R) + G_SR * (T_S - T_R) \
        - q_ri[2] - h_i * Ai_R * (T_R - T_gas)
    # rear wall: radiation in + convection - loss through 6" SuperIsol
    U_W = 1 / (GEO['t_sup'] / k_superisol(T_W) + prm['R_ext'])
    r[5] = -q_rad[4] + h_W * A_W * (T_cav - T_W) - U_W * A_W * (T_W - T_bldg)
    return r

def solve_thermal(mdot, P_elec, T_in, T_bldg, prm, T_plate_fixed=None, shape=None):
    """March the 10 segments for a given mass flow. Returns detailed state dict.
    If T_plate_fixed is given (transient use), the plate temperature is prescribed
    per segment and the heater equations are skipped; q into cavity is an output."""
    g = GEO
    Lseg = g['L_heated'] / NSEG
    if shape is None:
        shape = np.ones(NSEG)
    shape = np.asarray(shape) / np.mean(shape)
    q_segs = P_elec * (1 - prm['f_edge_loss']) / NSEG * shape
    T_cav = T_in + 60.0
    state = None
    for outer in range(80):
        T_gas = T_in
        rows = []
        Q_gas_tot = 0.0
        Q_conv_cav_ducts = 0.0
        Q_conv_cav_plate = 0.0
        Q_wall_loss = 0.0
        hA_sum = 0.0
        hAT_sum = 0.0
        guess = None
        for i in range(NSEG):
            q_seg = q_segs[i]
            z_mid = (i + 0.5) * Lseg
            rho, cp, mu, k, Pr = air(T_gas + 20)
            Re = mdot / g['A_flow'] * g['Dh'] / mu
            x_from_inlet = z_mid - g['z_riser_bot']
            h_i = h_internal(Re, Pr, k, g['Dh'], x_from_inlet)
            if guess is None:
                guess = np.array([T_gas + 500, T_gas + 380, T_gas + 150,
                                  T_gas + 110, T_gas + 90, T_gas + 120])
            Ai_F = g['n_ducts'] * g['duct_in_n'] * Lseg
            Ai_S = g['n_ducts'] * 2 * g['duct_in_w'] * Lseg
            Tg_mean = T_gas + 6.0
            for _sub in range(4):    # make wall solve consistent with gas mean temp
                if T_plate_fixed is None:
                    sol, info, ier, _ = fsolve(segment_balance, guess,
                                               args=(q_seg, T_cav, Tg_mean, h_i,
                                                     T_bldg, prm),
                                               full_output=True, xtol=1e-8)
                    if ier != 1:   # retry from a flux-based cold start
                        g0 = np.array([T_gas + 480, T_gas + 350, T_gas + 110,
                                       T_gas + 70, T_gas + 60, T_gas + 100])
                        sol, info, ier, _ = fsolve(segment_balance, g0,
                                                   args=(q_seg, T_cav, Tg_mean,
                                                         h_i, T_bldg, prm),
                                                   full_output=True, xtol=1e-8)
                else:
                    # prescribe T_P; solve remaining 5 (drop heater eq, plate eq)
                    Tp = T_plate_fixed[i]

                    def res5(y):
                        xx = np.array([Tp + 100, Tp, y[0], y[1], y[2], y[3]])
                        rr = segment_balance(xx, q_seg, T_cav, Tg_mean, h_i,
                                             T_bldg, prm)
                        return rr[2:6]
                    y = fsolve(res5, guess[2:6], xtol=1e-8)
                    sol = np.array([Tp, Tp, *y])
                guess = sol.copy()
                T_h, T_P, T_F, T_S, T_R, T_W = sol
                Qg = h_i * (Ai_F * (T_F - Tg_mean) + Ai_S * (T_S - Tg_mean)
                            + Ai_F * (T_R - Tg_mean))
                Tg_out = T_gas + Qg / (mdot * cp)
                Tg_new = 0.5 * (T_gas + Tg_out)
                if abs(Tg_new - Tg_mean) < 0.05:
                    Tg_mean = Tg_new
                    break
                Tg_mean = Tg_new
            # bookkeeping for cavity-air balance
            L = g['L_heated']
            A_P, A_F, A_S, A_R, A_W = A_CAV
            faces = [(h_natural_vertical(T_P, T_cav, L), A_P, T_P),
                     (h_natural_vertical(T_F, T_cav, L), A_F, T_F),
                     (0.7 * h_natural_vertical(T_S, T_cav, L), A_S, T_S),
                     (0.7 * h_natural_vertical(T_R, T_cav, L), A_R, T_R),
                     (0.7 * h_natural_vertical(T_W, T_cav, L), A_W, T_W)]
            for h, A, Ts in faces:
                hA_sum += h * A
                hAT_sum += h * A * Ts
            Q_conv_cav_plate += faces[0][0] * A_P * (T_P - T_cav)
            # convective heat delivered by cavity air to the duct faces
            Q_conv_cav_ducts += sum(h * A * (T_cav - Ts) for h, A, Ts in faces[1:4])
            U_W = 1 / (g['t_sup'] / k_superisol(T_W) + prm['R_ext'])
            Q_wall_loss += U_W * A_W * (T_W - T_bldg)
            rows.append(dict(z=z_mid, T_h=T_h, T_P=T_P, T_F=T_F, T_S=T_S,
                             T_R=T_R, T_W=T_W, T_gas_in=T_gas, T_gas_out=Tg_out,
                             Q_gas=Qg, h_i=h_i, Re=Re))
            Q_gas_tot += Qg
            T_gas = Tg_out
        # cavity-air balance: sum hA(Ts - T_cav) = sidewall loss. Weighted-mean update.
        A_side = 2 * g['cav_depth'] * g['L_heated'] + 2 * g['cav_width'] * g['cav_depth']
        U_side = 1 / (g['t_sup'] / k_superisol(T_cav) + prm['R_ext'])
        T_new = (hAT_sum + U_side * A_side * T_bldg) / (hA_sum + U_side * A_side)
        dT = T_new - T_cav
        T_cav += 0.7 * dT
        if abs(dT) < 0.01:
            break
    state = dict(rows=rows, T_cav=T_cav, Q_gas=Q_gas_tot,
                 Q_sidewall=U_side * A_side * (T_cav - T_bldg),
                 Q_rearwall=Q_wall_loss, T_gas_out=T_gas)
    return state

# ----------------------------------------------------------------------------- hydraulics
def loop_dp(mdot, state, T_in, T_bldg, T_out, wind, prm, detail=None):
    """Driving buoyancy minus friction, Pa (positive = accelerating)."""
    g = GEO
    rows = state['rows']
    T_exit = state['T_gas_out']
    # chimney heat loss through Enerwrap (vertical, insulated) -> small dT
    rho_h, cp_h, mu_h, k_h, Pr_h = air(T_exit)
    A_ch_surf = np.pi * g['D_chim'] * (g['z_chim_top'] - g['z_port']) * 2
    U_ch = 1 / (g['t_wrap'] / k_enerwrap(T_exit) + prm['R_ext'] + 0.1)
    dT_ch = U_ch * A_ch_surf * (T_exit - T_out) / (mdot * cp_h)
    T_chim = T_exit - 0.5 * dT_ch

    # ---- buoyancy: g * [ rho_amb*(z_dis - z_A) - sum(rho_i * dz_i along loop) ]
    rho_amb = rho_air(T_out)
    z_A = g['z_intake']
    path = []
    path.append((rho_air(T_bldg), -(z_A - (-0.65))))            # downcomer descent
    path.append((rho_air(T_in), (0 - (-0.65))))                 # plenum + unheated riser stub
    for r in rows:                                              # heated riser
        Tm = 0.5 * (r['T_gas_in'] + r['T_gas_out'])
        path.append((rho_air(Tm), g['L_heated'] / NSEG))
    path.append((rho_air(T_exit), g['z_riser_top'] - g['L_heated']))   # riser above heat
    path.append((rho_air(T_exit), g['z_port'] - g['z_riser_top']))     # outlet plenum
    path.append((rho_air(T_chim), g['z_discharge'] - g['z_port']))     # chimney rise
    dp_buoy = G_GRAV * (rho_amb * (g['z_discharge'] - z_A)
                        - sum(r * dz for r, dz in path))
    # wind at discharge: suction if Cp<0
    dp_wind = -prm['Cp_wind'] * 0.5 * rho_amb * wind ** 2

    # ---- friction
    dp = 0.0
    # downcomer at building temperature
    rho_d, cp_d, mu_d, k_d, _ = air(T_bldg)
    V = mdot / (rho_d * np.pi / 4 * g['D_dc'] ** 2)
    Re = rho_d * V * g['D_dc'] / mu_d
    f = f_churchill(Re, prm['rough'] / g['D_dc'])
    K = 0.5 + prm['K_conditioner'] + 0.3 + 1.0          # inlet + conditioner + elbow + exit
    dp += (f * g['L_dc'] / g['D_dc'] + K) * 0.5 * rho_d * V ** 2
    # risers: per-segment friction with local properties + inlet/outlet K + acceleration
    Gm = mdot / g['A_flow']
    rho_in_r = rho_air(T_in)
    dp += 0.4 * 0.5 * Gm ** 2 / rho_in_r                # contraction into ducts
    for r in rows:
        Tm = 0.5 * (r['T_gas_in'] + r['T_gas_out'])
        rho_s, cp_s, mu_s, k_s, _ = air(Tm)
        Re_s = Gm * g['Dh'] / mu_s
        f_s = f_churchill(Re_s, prm['rough'] / g['Dh'])
        dp += f_s * (g['L_heated'] / NSEG) / g['Dh'] * 0.5 * Gm ** 2 / rho_s
    # unheated riser lengths
    rho_e = rho_air(T_exit)
    L_unheated = g['duct_len'] - g['L_heated']
    Re_e = Gm * g['Dh'] / air(T_exit)[2]
    dp += f_churchill(Re_e, prm['rough'] / g['Dh']) * L_unheated / g['Dh'] \
        * 0.5 * Gm ** 2 / rho_e
    dp += 1.0 * 0.5 * Gm ** 2 / rho_e                   # expansion into outlet plenum
    dp += Gm ** 2 * (1 / rho_e - 1 / rho_in_r)          # acceleration
    # chimney (both stacks, total area)
    V_c = mdot / (rho_air(T_chim) * g['A_chim'])
    rho_c = rho_air(T_chim)
    Re_c = rho_c * V_c * g['D_chim'] / air(T_chim)[2]
    f_c = f_churchill(Re_c, prm['rough'] / g['D_chim'])
    L_eq = g['L_chim_vert_eq'] + g['L_chim_horz_eq']
    K_c = 0.5 + prm['K_dampers'] + 1.0                  # port entry + dampers + exit
    dp_chim = (f_c * L_eq / g['D_chim'] + K_c) * 0.5 * rho_c * V_c ** 2
    dp += dp_chim
    if detail is not None:
        detail.update(dp_buoy=dp_buoy, dp_wind=dp_wind, dp_fric=dp,
                      dp_chim=dp_chim, T_chim=T_chim, dT_chimney_loss=dT_ch)
    return dp_buoy + dp_wind - dp

# ----------------------------------------------------------------------------- full solve
def steady_solve(P_elec=82e3, T_out=275.15, T_bldg=293.15, wind=0.0,
                 prm=None, T_plate_fixed=None, shape=None, mdot_bracket=(0.05, 4.0)):
    prm = {**PARAMS, **(prm or {})}
    T_in = T_bldg          # inlet air = building air (downcomer uninsulated, indoors)

    cache = {}

    def mom(mdot):
        st = solve_thermal(mdot, P_elec, T_in, T_bldg, prm, T_plate_fixed, shape)
        cache['st'] = st
        return loop_dp(mdot, st, T_in, T_bldg, T_out, wind, prm)

    mdot = brentq(mom, *mdot_bracket, xtol=1e-4, rtol=1e-5)
    st = cache['st']
    st['mdot'] = mdot
    st['prm'] = prm
    st['P_elec'] = P_elec
    # summary numbers
    rows = st['rows']
    st['dT_riser'] = st['T_gas_out'] - T_in
    st['T_in'] = T_in
    # mid-plane (z=3.5 m) values: interpolate between segments 5 and 6 (z=3.35, 4.02)
    zs = np.array([r['z'] for r in rows])
    def mid(key):
        return float(np.interp(3.5, zs, [r[key] for r in rows]))
    st['mid'] = {k: mid(k) for k in ['T_h', 'T_P', 'T_F', 'T_S', 'T_R', 'T_W']}
    st['mid']['T_gas'] = float(np.interp(
        3.5, zs, [0.5 * (r['T_gas_in'] + r['T_gas_out']) for r in rows]))
    st['T_plate_mean'] = float(np.mean([r['T_P'] for r in rows]))
    st['T_plate_max'] = float(np.max([r['T_P'] for r in rows]))
    # energy audit + radiation/convection split on the ducts
    Q_rad_ducts = 0.0
    Q_conv_ducts = 0.0
    g = GEO
    eps = np.array([prm['eps_plate'], prm['eps_duct'], prm['eps_duct'],
                    prm['eps_duct'], prm['eps_wall']])
    for r in rows:
        q_rad = radiosity_net([r['T_P'], r['T_F'], r['T_S'], r['T_R'], r['T_W']],
                              A_CAV, F_CAV, eps)
        Q_rad_ducts += -(q_rad[1] + q_rad[2] + q_rad[3])       # net absorbed by duct faces
        L = g['L_heated']
        A_P, A_F, A_S, A_R, A_W = A_CAV
        Q_conv_ducts += (h_natural_vertical(r['T_F'], st['T_cav'], L) * A_F
                         * (st['T_cav'] - r['T_F'])
                         + 0.7 * h_natural_vertical(r['T_S'], st['T_cav'], L) * A_S
                         * (st['T_cav'] - r['T_S'])
                         + 0.7 * h_natural_vertical(r['T_R'], st['T_cav'], L) * A_R
                         * (st['T_cav'] - r['T_R']))
    st['Q_rad_ducts'] = Q_rad_ducts
    st['Q_conv_ducts'] = Q_conv_ducts
    tot = Q_rad_ducts + Q_conv_ducts
    st['rad_fraction'] = Q_rad_ducts / tot if tot else np.nan
    # per-face cavity-side fluxes (what the Riser-7 heat-flux sensors see), W/m^2
    flux = {f: {'rad': [], 'conv': []} for f in ['front', 'side', 'rear']}
    for r in rows:
        q_rad = radiosity_net([r['T_P'], r['T_F'], r['T_S'], r['T_R'], r['T_W']],
                              A_CAV, F_CAV, eps)
        L = g['L_heated']
        A_P, A_F, A_S, A_R, A_W = A_CAV
        flux['front']['rad'].append(-q_rad[1] / A_F)
        flux['side']['rad'].append(-q_rad[2] / A_S)
        flux['rear']['rad'].append(-q_rad[3] / A_R)
        flux['front']['conv'].append(
            h_natural_vertical(r['T_F'], st['T_cav'], L) * (st['T_cav'] - r['T_F']))
        flux['side']['conv'].append(
            0.7 * h_natural_vertical(r['T_S'], st['T_cav'], L) * (st['T_cav'] - r['T_S']))
        flux['rear']['conv'].append(
            0.7 * h_natural_vertical(r['T_R'], st['T_cav'], L) * (st['T_cav'] - r['T_R']))
    st['flux_mid'] = {f: {k: float(np.interp(3.5, zs, v))
                          for k, v in d.items()} for f, d in flux.items()}
    det = {}
    loop_dp(mdot, st, T_in, T_bldg, T_out, wind, prm, detail=det)
    st['dp'] = det
    # parasitics
    st['Q_back_loss'] = P_elec * (1 - prm['f_edge_loss']) - sum(
        _heater_forward(r, prm) for r in rows)
    st['Q_edge_loss'] = P_elec * prm['f_edge_loss']
    return st

def _heater_forward(r, prm):
    Rr = 1 / prm['eps_heater'] + 1 / prm['eps_plate_back'] - 1
    return GEO['A_plate'] / NSEG * SIGMA * (r['T_h'] ** 4 - r['T_P'] ** 4) / Rr

# ----------------------------------------------------------------------------- reporting
def C(K):
    return K - 273.15

def report(st, label=""):
    rows = st['rows']
    m = st['mid']
    lines = [f"=== {label} ===",
             f"mass flow            : {st['mdot']:.3f} kg/s  ({st['mdot']*60:.1f} kg/min)",
             f"riser gas dT         : {st['dT_riser']:.1f} K   "
             f"(in {C(st['T_in']):.1f} C -> out {C(st['T_gas_out']):.1f} C)",
             f"cavity air           : {C(st['T_cav']):.1f} C",
             f"mid-plane (z=3.5 m)  : plate {C(m['T_P']):.0f} C | duct front {C(m['T_F']):.0f} C"
             f" | sides {C(m['T_S']):.0f} C | rear {C(m['T_R']):.0f} C | backwall {C(m['T_W']):.0f} C"
             f" | gas {C(m['T_gas']):.0f} C",
             f"plate mean/max       : {C(st['T_plate_mean']):.0f} / {C(st['T_plate_max']):.0f} C",
             f"heater mean          : {C(np.mean([r['T_h'] for r in rows])):.0f} C",
             f"Q to gas             : {st['Q_gas']/1e3:.1f} kW of {st['P_elec']/1e3:.1f} kWe",
             f"  rad to ducts       : {st['Q_rad_ducts']/1e3:.1f} kW | conv to ducts "
             f"{st['Q_conv_ducts']/1e3:.1f} kW -> radiative fraction {st['rad_fraction']:.2f}",
             f"  heater back loss   : {st['Q_back_loss']/1e3:.1f} kW | edge assump "
             f"{st['Q_edge_loss']/1e3:.1f} kW | rear-wall {st['Q_rearwall']/1e3:.2f} kW"
             f" | sidewall {st['Q_sidewall']/1e3:.2f} kW",
             ]
    return "\n".join(lines)

if __name__ == "__main__":
    st = steady_solve(P_elec=82e3, T_out=275.15, T_bldg=293.15, wind=0.0)
    print(report(st, "Case 1 baseline: 82 kWe, outdoor +2 C, building 20 C, no wind"))

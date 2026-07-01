"""
Coupled natural-circulation loop solver for the RCCS test facility.

Structure (see calculation_note.md for the full derivation):
  Stage A (cavity):    plate <-radiation + sealed-cavity natural convection-> riser FRONT face
  Ring (riser wall):   front face -> circumferential conduction -> side/rear faces,
                       each face losing heat by internal duct convection to the
                       local bulk air stream
  Stage B (duct):      riser inner wall -> forced/buoyancy duct convection -> bulk air
  Loop momentum:       buoyancy (density deficit, full loop height) = friction
                       (duct friction + minor losses), solved for m_dot.

Axial marching (uniform axial heat-input case): the riser height is split into N
slices; because heat input per slice is fixed by the (given) axial power shape
and total power, energy conservation lets the wall-ring problem be solved
IN A FORWARD, NON-ITERATIVE way per slice (see comments in march_riser).
"""
import numpy as np
from scipy.optimize import brentq

import air_properties as air
import geometry as G
import radiation as rad
import convection as conv


def air_props(T):
    """Return (rho, mu, cp, k, Pr, beta) at temperature T [K]."""
    return (air.rho_air(T), air.mu_air(T), air.cp_air(T), air.k_air(T),
            air.pr_air(T), air.beta_air(T))


# ---- view factor (geometry-fixed; computed once) --------------------------
F12, F_FULL, AREA_FRAC = rad.plate_to_riserfront_view_factor(
    G.CAVITY_WIDTH, G.CAVITY_HEIGHT, G.CAVITY_DEPTH_BASELINE,
    G.RISER_FRONT_FACE_AREA_TOTAL)
A_PLATE = 8.82  # m^2; see geometry.py note on the as-built-vs-scaling-table area choice

# ---- riser wall ring geometry (per single riser) ---------------------------
W_F = G.RISER_ID_NARROW      # front (and rear) face inner width
W_S = G.RISER_ID_WIDE        # each side face inner width
T_WALL = G.RISER_WALL_T
K_WALL = G.RISER_K
L_PATH = 0.5 * W_F + 0.5 * W_S   # conduction path length, face-center to face-center


def ring_solve(Q_ext_F_per_riser, h_int, dz):
    """Solve the 3-node (Front/Side-combined/Rear) circumferential ring for one
    riser, one axial slice of height dz, with all external heat entering at F
    and convective loss to the (locally uniform) bulk air baked into the
    matrix (T_air subtracted out -> solve for T-T_air directly, linear)."""
    R1 = L_PATH / (K_WALL * T_WALL * dz)          # single F-S (or S-R) path, one side
    R_FS = R1 / 2.0                                # two symmetric paths in parallel
    R_SR = R1 / 2.0
    hA_F = h_int * W_F * dz
    hA_S = h_int * (2 * W_S) * dz
    hA_R = h_int * W_F * dz

    # Unknowns x = [dTF, dTS, dTR] (temperature rise above local bulk air)
    A_mat = np.array([
        [1.0 / R_FS + hA_F, -1.0 / R_FS, 0.0],
        [-1.0 / R_FS, 1.0 / R_FS + 1.0 / R_SR + hA_S, -1.0 / R_SR],
        [0.0, -1.0 / R_SR, 1.0 / R_SR + hA_R],
    ])
    b_vec = np.array([Q_ext_F_per_riser, 0.0, 0.0])
    dT = np.linalg.solve(A_mat, b_vec)
    return dT  # [dT_F, dT_S, dT_R] above local T_air


def _cavity_split(Tp, T_F, gap):
    """Radiative and convective heat transfer *coefficients* referenced to the
    total riser-front area, i.e. q_rad = h_rad*A2*(Tp-T_F), q_conv = h_cav*A2*(Tp-T_F)."""
    q_rad_full = rad.three_surface_exchange(Tp, T_F, A_PLATE, G.RISER_FRONT_FACE_AREA_TOTAL,
                                             F12, G.PLATE_EMISSIVITY, G.RISER_EMISSIVITY)
    h_rad = q_rad_full / (G.RISER_FRONT_FACE_AREA_TOTAL * max(Tp - T_F, 1e-6))
    h_cav, Ra, Nu = conv.h_cavity_natural_convection(Tp, T_F, gap, G.CAVITY_HEIGHT,
                                                      G.CAVITY_WIDTH, air_props)
    return h_rad, h_cav, Ra, Nu


def solve_plate_temp_seg(dQ_seg, T_F, A2_seg, gap=G.CAVITY_DEPTH_BASELINE,
                          T_guess_hi=2000.0):
    """dQ_seg: heat [W] that must cross the cavity for this axial slice.
    A2_seg: riser-front area of this slice [m^2] (fraction of total).
    Plate is always hotter than the riser front (heat flows plate->riser), so
    bracket strictly above T_F to avoid the (Tp-T_F)->0 singularity in h_rad."""
    T_guess_lo = T_F + 1.0
    def resid(Tp):
        h_rad, h_cav, Ra, Nu = _cavity_split(Tp, T_F, gap)
        return (h_rad + h_cav) * A2_seg * (Tp - T_F) - dQ_seg
    if resid(T_guess_hi) < 0:
        T_guess_hi = 4000.0
    Tp = brentq(resid, T_guess_lo, T_guess_hi, xtol=1e-6, rtol=1e-10)
    h_rad, h_cav, Ra, Nu = _cavity_split(Tp, T_F, gap)
    q_rad = h_rad * A2_seg * (Tp - T_F)
    q_conv = h_cav * A2_seg * (Tp - T_F)
    return Tp, q_rad, q_conv, Ra, Nu


def riser_reynolds(m_dot, T_air):
    """Re_Dh for ONE riser (flow split evenly across N_RISERS), and per-riser velocity."""
    rho, mu, cp, k, Pr, beta = air_props(T_air)
    m_dot_1 = m_dot / G.N_RISERS
    V = m_dot_1 / (rho * G.RISER_FLOW_AREA_1)
    Re = rho * V * G.RISER_DH / mu
    return Re, V, rho, mu, cp, k, Pr


def axial_power_weights(N, shape="uniform"):
    if shape == "uniform":
        return np.ones(N) / N
    raise ValueError(shape)


def march_riser(m_dot, T_in, Q_net, N=40, axial_shape="uniform",
                 gap=G.CAVITY_DEPTH_BASELINE):
    """March up the riser, slice by slice, solving the ring + plate-temperature
    problem at each slice (both are algebraic given the slice's dQ_seg, which is
    fixed by the axial power shape and independent of the loop solution)."""
    dz = G.RISER_LENGTH_HEATED / N
    weights = axial_power_weights(N, axial_shape)
    dQ = Q_net * weights                      # heat per slice, TOTAL over 12 risers
    dQ_per_riser = dQ / G.N_RISERS
    A2_total = G.RISER_FRONT_FACE_AREA_TOTAL
    A2_seg = A2_total * weights                # matches uniform-height slicing since
                                                 # front area is uniform per unit height

    T_air = np.zeros(N + 1)
    T_air[0] = T_in
    T_plate = np.zeros(N)
    T_F = np.zeros(N)
    T_S = np.zeros(N)
    T_R = np.zeros(N)
    q_rad = np.zeros(N)
    q_conv_cav = np.zeros(N)
    Re_arr = np.zeros(N)

    for i in range(N):
        T_air_local = T_air[i]  # use inlet-of-slice bulk temp (marching estimate)
        Re, V, rho, mu, cp, k, Pr = riser_reynolds(m_dot, T_air_local)
        Nu = conv.nu_riser_internal(Re, Pr)
        h_int = Nu * k / G.RISER_DH
        Re_arr[i] = Re

        # --- Step 1: ring solve gives dT of each face above local T_air ---
        dT = ring_solve(dQ_per_riser[i], h_int, dz)
        T_F[i] = T_air_local + dT[0]
        T_S[i] = T_air_local + dT[1]
        T_R[i] = T_air_local + dT[2]

        # --- Step 2: plate temperature from the cavity radiation+convection ---
        Tp, qr, qc, Ra, Nu_cav = solve_plate_temp_seg(dQ[i], T_F[i], A2_seg[i], gap)
        T_plate[i] = Tp
        q_rad[i] = qr
        q_conv_cav[i] = qc

        # --- Step 3: march bulk air temperature up this slice ---
        m_dot_safe = max(m_dot, 1e-6)
        T_air[i + 1] = T_air_local + dQ[i] / (m_dot_safe * cp)

    return dict(z=np.linspace(0, G.RISER_LENGTH_HEATED, N + 1), T_air=T_air,
                T_plate=T_plate, T_F=T_F, T_S=T_S, T_R=T_R,
                q_rad=q_rad, q_conv_cav=q_conv_cav, Re=Re_arr, dz=dz,
                Q_rad_total=q_rad.sum(), Q_conv_total=q_conv_cav.sum())


# ------------------------------------------------------------------ chimney -
CHIMNEY_ENERWRAP_T = 3 * 0.0254   # m, 3 in
CHIMNEY_OD_PERIM_PER_DUCT = np.pi * G.CHIMNEY_D  # crude (thin duct) perimeter


def chimney_outlet_temp(T_out_riser, T_amb, m_dot, k_ins=0.06):
    """Simple duct-heat-loss exponential decay along the chimney length,
    using the insulated round duct as a fin-type heat loss to ambient.
    U based on Enerwrap-80 conduction resistance only (dominant vs internal/
    external convection for a well-insulated duct) -- standard duct-heat-loss
    formula T(x)-Tamb = (Tin-Tamb) exp(-U*P*x/(mdot*cp))."""
    if m_dot <= 1e-6:
        return T_out_riser
    rho, mu, cp, k, Pr, beta = air_props(T_out_riser)
    R_ins_per_area = CHIMNEY_ENERWRAP_T / k_ins   # m^2K/W, conduction-only (rough)
    U = 1.0 / R_ins_per_area
    P_total = G.N_CHIMNEYS * CHIMNEY_OD_PERIM_PER_DUCT
    L = G.CHIMNEY_VERT_LEN  # conservative: use full flow length as duct length
    exponent = -U * P_total * L / (m_dot * cp)
    return T_amb + (T_out_riser - T_amb) * np.exp(exponent)


# --------------------------------------------------------------- buoyancy ---
def buoyancy_pressure(m_dot, T_in, T_amb, riser_result, T_out_chimney):
    """Integrate density deficit over the full loop height (riser bottom, z=0,
    to chimney exit, z=Z_CHIMNEY_EXIT); reference column is ambient air at the
    same height (valid because the downcomer/inlet plenum run at ~T_amb)."""
    z_riser = riser_result["z"]
    T_riser = riser_result["T_air"]
    rho_amb = air.rho_air(T_amb)

    rho_riser = air.rho_air(T_riser)
    integral_riser = np.trapezoid(rho_amb - rho_riser, z_riser)

    z1 = G.RISER_LENGTH_HEATED
    z2 = G.Z_OUTLET_PLENUM_PORT
    T_out = T_riser[-1]
    rho_out = air.rho_air(T_out)
    integral_outlet_plenum = (rho_amb - rho_out) * (z2 - z1)

    z3 = G.Z_CHIMNEY_EXIT
    T_ch_avg = 0.5 * (T_out + T_out_chimney)
    rho_ch_avg = air.rho_air(T_ch_avg)
    integral_chimney = (rho_amb - rho_ch_avg) * (z3 - z2)

    dp = air.G * (integral_riser + integral_outlet_plenum + integral_chimney)
    return dp


# --------------------------------------------------------------- friction ---
ROUGHNESS = {
    "steel_oxidized": 0.15e-3,   # m, "galvanized/oxidized steel", Moody-chart typical
    "aluminum": 0.03e-3,
    "galvanized": 0.15e-3,
}


def friction_pressure(m_dot, T_in, T_amb, riser_result, T_out_chimney):
    """Sum Darcy-Weisbach duct friction + minor losses over the whole loop.
    Loss-coefficient values are stated, generic, order-of-magnitude engineering
    estimates (Idelchik/Crane-TP410-type values); flagged in the calc note as
    the single largest source of uncertainty in the momentum balance."""
    T_out = riser_result["T_air"][-1]
    dp_total = 0.0
    details = {}

    # ---- downcomer (ambient temperature air) ----
    rho, mu, cp, k, Pr, beta = air_props(T_in)
    V = m_dot / (rho * G.DOWNCOMER_AREA)
    Re = rho * V * G.DOWNCOMER_D / mu
    f = conv.darcy_friction_factor(Re, ROUGHNESS["steel_oxidized"] / G.DOWNCOMER_D)
    dp_fric = f * (G.DOWNCOMER_LEN_EQUIV / G.DOWNCOMER_D) * 0.5 * rho * V**2
    K_entrance, K_conditioner = 0.5, 1.0
    dp_minor = (K_entrance + K_conditioner) * 0.5 * rho * V**2
    details["downcomer"] = dp_fric + dp_minor
    dp_total += dp_fric + dp_minor

    # ---- inlet plenum transition (expansion + turn + contraction into risers) ----
    K_plenum_in = 1.5
    dp_total += K_plenum_in * 0.5 * rho * V**2
    details["inlet_plenum"] = K_plenum_in * 0.5 * rho * V**2

    # ---- riser ducts (12 parallel) ----
    T_air_prof = riser_result["T_air"]
    z_prof = riser_result["z"]
    dp_riser = 0.0
    for i in range(len(z_prof) - 1):
        T_mid = 0.5 * (T_air_prof[i] + T_air_prof[i + 1])
        rho_i, mu_i, cp_i, k_i, Pr_i, beta_i = air_props(T_mid)
        V_i = (m_dot / G.N_RISERS) / (rho_i * G.RISER_FLOW_AREA_1)
        Re_i = rho_i * V_i * G.RISER_DH / mu_i
        f_i = conv.darcy_friction_factor(Re_i, ROUGHNESS["steel_oxidized"] / G.RISER_DH)
        dz = z_prof[i + 1] - z_prof[i]
        dp_riser += f_i * (dz / G.RISER_DH) * 0.5 * rho_i * V_i**2
    K_riser_entrance, K_riser_exit = 0.5, 0.5
    rho_in, mu_in, cp_in, k_in, Pr_in, beta_in = air_props(T_in)
    V_in = (m_dot / G.N_RISERS) / (rho_in * G.RISER_FLOW_AREA_1)
    rho_out, *_ = air_props(T_out)
    V_out = (m_dot / G.N_RISERS) / (rho_out * G.RISER_FLOW_AREA_1)
    dp_riser += K_riser_entrance * 0.5 * rho_in * V_in**2
    dp_riser += K_riser_exit * 0.5 * rho_out * V_out**2
    details["risers"] = dp_riser
    dp_total += dp_riser

    # ---- outlet plenum transition ----
    K_plenum_out = 1.5
    dp_total += K_plenum_out * 0.5 * rho_out * V_out**2
    details["outlet_plenum"] = K_plenum_out * 0.5 * rho_out * V_out**2

    # ---- chimney (2 parallel) ----
    T_ch_avg = 0.5 * (T_out + T_out_chimney)
    rho_ch, mu_ch, cp_ch, k_ch, Pr_ch, beta_ch = air_props(T_ch_avg)
    V_ch = (m_dot / G.N_CHIMNEYS) / (rho_ch * G.CHIMNEY_AREA_EACH)
    Re_ch = rho_ch * V_ch * G.CHIMNEY_D / mu_ch
    f_ch = conv.darcy_friction_factor(Re_ch, ROUGHNESS["galvanized"] / G.CHIMNEY_D)
    L_ch = G.CHIMNEY_VERT_LEN + G.CHIMNEY_HORIZ_LEN
    dp_ch = f_ch * (L_ch / G.CHIMNEY_D) * 0.5 * rho_ch * V_ch**2
    K_damper_bends_exit = 0.5 + 2 * 0.3 + 1.0  # damper + 2 bends + discharge exit loss
    dp_ch += K_damper_bends_exit * 0.5 * rho_ch * V_ch**2
    details["chimney"] = dp_ch
    dp_total += dp_ch

    return dp_total, details


def wind_stack_pressure(V_wind, T_amb, Cp=-0.4):
    """Wind blowing across an open vertical stack mouth generally induces a
    local suction (flow separation / aspirator effect) that AUGMENTS natural
    draft; the opposite sign (downwash suppressing draft) is also physically
    possible depending on the (unspecified) stack-cap geometry. There is no
    stack-cap detail in the inputs, so this is modeled with a wind-pressure
    coefficient Cp (dp = -Cp * 0.5*rho*V^2, generic building/stack aerodynamics
    convention, e.g. ASHRAE Fundamentals Ch. 24) with a literature-typical
    default Cp=-0.4 (net-aiding) and an explicit +/- sensitivity band
    (Cp in [-0.8, +0.3]) reported separately -- this is one of the largest
    stated uncertainties in the weather-sensitivity case."""
    rho_amb = air.rho_air(T_amb)
    return -Cp * 0.5 * rho_amb * V_wind**2


# ---------------------------------------------------------- top-level solve
def parasitic_loss_fraction(Q_electric, T_plate_est, T_amb):
    """Estimate parasitic (backside/side-wall) conduction losses as a fraction
    of electric power, from the insulation conductivities given in inputs/02,
    evaluated at a representative hot-face temperature. Two paths:
      (1) Duraboard LD behind the ceramic heaters (2 in, backside of plate/heater
          assembly to room air)
      (2) SuperIsol on the N/S/W cavity walls (6 in, cavity-air-side to room air)
    Both are one-off engineering estimates -- flagged as a leading uncertainty.
    """
    T_hot_backside = T_plate_est  # assume heater backside ~ plate temperature
    k_dura = 0.1442 * np.interp(T_hot_backside - 273.15, [204, 538], [0.55, 0.847])
    t_dura = 2 * 0.0254
    Q_dura = k_dura * A_PLATE * (T_hot_backside - T_amb) / t_dura

    T_cavity_avg = 0.6 * T_plate_est + 0.4 * T_amb  # rough cavity-air estimate
    k_super = 0.1442 * np.interp(T_cavity_avg - 273.15, [204, 399, 593],
                                  [0.416, 0.554, 0.693])
    t_super = 6 * 0.0254
    A_walls = (2 * G.CAVITY_DEPTH_BASELINE + G.CAVITY_WIDTH) * G.CAVITY_HEIGHT
    Q_super = k_super * A_walls * (T_cavity_avg - T_amb) / t_super

    Q_loss = Q_dura + Q_super
    return min(Q_loss / Q_electric, 0.3), Q_dura, Q_super


def solve_case(Q_electric, T_amb, T_inlet, wind_speed=0.0, Cp_wind=-0.4, N=40,
               gap=G.CAVITY_DEPTH_BASELINE, axial_shape="uniform",
               parasitic_iters=8, parasitic_tol=1e-4):
    """Full self-consistent solve: parasitic loss <-> plate temp <-> loop
    mass flow, iterated to a fixed point (Q_net <-> T_plate <-> f_loss) so the
    returned (rr, m_dot, f_loss, Q_net) are all mutually consistent."""
    Q_net = Q_electric
    f_loss, Q_dura, Q_super = 0.0, 0.0, 0.0
    rr, m_dot = None, None

    def mismatch(m_dot_try, Q_net_try):
        try:
            rr_try = march_riser(m_dot_try, T_inlet, Q_net_try, N=N,
                                  axial_shape=axial_shape, gap=gap)
            T_out_ch_try = chimney_outlet_temp(rr_try["T_air"][-1], T_amb, m_dot_try)
            dp_b = buoyancy_pressure(m_dot_try, T_inlet, T_amb, rr_try, T_out_ch_try)
            dp_wind = wind_stack_pressure(wind_speed, T_amb, Cp_wind)
            dp_f, _ = friction_pressure(m_dot_try, T_inlet, T_amb, rr_try, T_out_ch_try)
            return dp_b + dp_wind - dp_f
        except (ValueError, FloatingPointError):
            # too little flow to carry the imposed heat -- solver runs into
            # extreme temperatures; this only happens well below the real
            # operating point, where buoyancy >> friction, so report a large
            # positive mismatch (push the bracket search to larger m_dot)
            return 1e9

    for _ in range(parasitic_iters):
        m_lo, m_hi = 0.05, 3.0
        lo_val, hi_val = mismatch(m_lo, Q_net), mismatch(m_hi, Q_net)
        while lo_val * hi_val > 0 and m_hi < 50.0:
            m_hi *= 2
            hi_val = mismatch(m_hi, Q_net)
        m_dot = brentq(lambda m: mismatch(m, Q_net), m_lo, m_hi, xtol=1e-6, rtol=1e-8)

        rr = march_riser(m_dot, T_inlet, Q_net, N=N, axial_shape=axial_shape, gap=gap)
        T_plate_est = rr["T_plate"].mean()
        f_loss, Q_dura, Q_super = parasitic_loss_fraction(Q_electric, T_plate_est, T_amb)
        Q_net_new = Q_electric * (1 - f_loss)
        if abs(Q_net_new - Q_net) / Q_electric < parasitic_tol:
            Q_net = Q_net_new
            break
        Q_net = Q_net_new
    else:
        # loop exhausted without meeting tol -- do one final consistent solve
        # at the last Q_net so the returned rr/m_dot match the returned Q_net
        m_lo, m_hi = 0.05, 3.0
        lo_val, hi_val = mismatch(m_lo, Q_net), mismatch(m_hi, Q_net)
        while lo_val * hi_val > 0 and m_hi < 50.0:
            m_hi *= 2
            hi_val = mismatch(m_hi, Q_net)
        m_dot = brentq(lambda m: mismatch(m, Q_net), m_lo, m_hi, xtol=1e-6, rtol=1e-8)
        rr = march_riser(m_dot, T_inlet, Q_net, N=N, axial_shape=axial_shape, gap=gap)

    T_out_ch = chimney_outlet_temp(rr["T_air"][-1], T_amb, m_dot)
    dp_b = buoyancy_pressure(m_dot, T_inlet, T_amb, rr, T_out_ch)
    dp_wind = wind_stack_pressure(wind_speed, T_amb, Cp_wind)
    dp_f, dp_details = friction_pressure(m_dot, T_inlet, T_amb, rr, T_out_ch)

    z_mid = np.searchsorted(rr["z"], G.RISER_LENGTH_HEATED / 2)
    z_mid = min(z_mid, len(rr["T_F"]) - 1)

    return dict(m_dot=m_dot, riser=rr, T_out_chimney=T_out_ch,
                dp_buoy=dp_b, dp_wind=dp_wind, dp_fric=dp_f, dp_details=dp_details,
                Q_electric=Q_electric, Q_net=Q_net, f_loss=f_loss,
                Q_dura=Q_dura, Q_super=Q_super,
                T_plate_mid=rr["T_plate"][z_mid], T_F_mid=rr["T_F"][z_mid],
                T_S_mid=rr["T_S"][z_mid], T_R_mid=rr["T_R"][z_mid],
                idx_mid=z_mid, T_amb=T_amb, T_inlet=T_inlet, wind=wind_speed)


if __name__ == "__main__":
    res = solve_case(Q_electric=82000.0, T_amb=2.0 + 273.15, T_inlet=20.0 + 273.15)
    print(f"m_dot = {res['m_dot']*1000/16.6667:.3f} .. let's just print SI")
    print(f"m_dot = {res['m_dot']:.4f} kg/s = {res['m_dot']*60:.3f} kg/min")
    print(f"T_air in={res['riser']['T_air'][0]-273.15:.1f}C out={res['riser']['T_air'][-1]-273.15:.1f}C "
          f"dT={res['riser']['T_air'][-1]-res['riser']['T_air'][0]:.1f}C")
    print(f"T_plate(mid)={res['T_plate_mid']-273.15:.1f}C  T_F(mid)={res['T_F_mid']-273.15:.1f}C "
          f"T_S(mid)={res['T_S_mid']-273.15:.1f}C T_R(mid)={res['T_R_mid']-273.15:.1f}C")
    print(f"Q_rad_total={res['riser']['Q_rad_total']/1000:.2f} kW  "
          f"Q_conv_cav_total={res['riser']['Q_conv_total']/1000:.2f} kW  "
          f"rad frac={res['riser']['Q_rad_total']/(res['riser']['Q_rad_total']+res['riser']['Q_conv_total']):.3f}")
    print(f"f_loss={res['f_loss']*100:.1f}%  Q_dura={res['Q_dura']/1000:.2f}kW Q_super={res['Q_super']/1000:.2f}kW")
    print(f"dp_buoy={res['dp_buoy']:.3f} Pa  dp_fric={res['dp_fric']:.3f} Pa")
    print("dp_details:", {k: round(v,3) for k,v in res['dp_details'].items()})
    print("Re range in risers:", res['riser']['Re'].min(), res['riser']['Re'].max())

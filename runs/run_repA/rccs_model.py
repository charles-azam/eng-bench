"""
First-principles steady-state model of the RCCS natural-circulation air loop.

Physics chain (all built from inputs/ + textbook correlations, NO facility data):

  1. FLOW: buoyancy-driven loop. Stack driving head from the density difference
     between the cold external air column and the hot internal (riser+chimney)
     column is balanced against friction + form losses -> solves mass flow m_dot.
       dP_buoy(T's) = dP_loss(m_dot)
  2. ENERGY: Q_air = m_dot * cp * (T_out - T_in)  -> riser air temperature rise.
  3. INTERNAL CONVECTION (riser gas side): Gnielinski / Dittus-Boelter ->
     inner wall temperature.
  4. CAVITY TRANSFER (plate -> risers): parallel-plate gray radiation network
     with re-radiating adiabatic side walls, PLUS enclosed-cavity natural
     convection -> plate temperature and the radiation/convection split.

Correlations cited inline. Geometry from inputs/01, properties from inputs/02.
"""
import numpy as np
from scipy.optimize import brentq
import airprops as ap

g = 9.81
SIGMA = 5.670e-8

# ----------------------------------------------------------------------------
# GEOMETRY  (from inputs/01_facility_geometry.md)  -- SI
# ----------------------------------------------------------------------------
IN = 0.0254
# Riser duct: outer 10 x 2 in, wall 0.188 in -> internal 9.624 x 1.624 in
r_a = 9.624 * IN          # internal long side  = 0.2445 m
r_b = 1.624 * IN          # internal short side = 0.04125 m
A_riser = r_a * r_b                       # 0.01008 m^2 single-duct flow area
P_wet   = 2 * (r_a + r_b)                 # wetted perimeter 0.5715 m
Dh      = 4 * A_riser / P_wet             # hydraulic diameter ~0.0706 m
N_RISER = 12
L_heat  = 6.91                            # heated length inside cavity (272 in)
A_int_1 = P_wet * L_heat                  # internal wetted area, one riser
A_int   = A_int_1 * N_RISER               # total internal wetted area

# Front (hot) face width for radiation: the 2-in narrow face, per duct, over height
w_front = 2.0 * IN                        # outer narrow-face width
# Heated plate (mock RPV) -- radiating source
A_PLATE = 10.18                           # as-built heated-plate area, m^2 (inputs/01 sec3)
EPS_P   = 0.785                            # measured plate emissivity 0.78-0.79
EPS_R   = 0.80                            # riser oxidized steel (NOT reported; assumed, cited)
CAV_GAP = 0.7066                          # plate-to-riser-front spacing, m (baseline)
CAV_H   = 6.7                             # cavity height, m
CAV_W   = 1.32                            # cavity width, m (52 in)

# Loop elevations for the stack integral (m); balanced so isothermal -> 0 draft.
# Ascending hot legs: risers (6.9), outlet plenum (1.4), chimney (11.1).
# Descending cold legs: atmospheric return (15.6) at T_out-door, downcomer (3.8) at T_in.
H_RISER   = 6.91
H_OPLENUM = 1.40
H_CHIM    = 11.1
H_DOWNC   = 3.8
H_ATM     = H_RISER + H_OPLENUM + H_CHIM - H_DOWNC   # = 15.61 (closes the loop)

# Flow areas of ducts for loss calc
A_DOWNC = np.pi/4 * (24*IN)**2            # 24-in downcomer, 0.2919 m^2
A_CHIM  = 0.58                            # dual 24-in chimney total (inputs/01 sec6)

# Chimney: insulated, Enerwrap. Downcomer: uninsulated.
L_CHIM_EQ = (826 + 470) * IN              # equivalent chimney length ~32.9 m
L_DOWNC   = 184.5 * IN                    # 4.69 m

# ----------------------------------------------------------------------------
# FRICTION FACTOR
# ----------------------------------------------------------------------------
def darcy_f(Re, eps_rel=0.0):
    if Re < 2300:
        return 64.0 / max(Re, 1.0)
    # Churchill (smooth-ish steel duct); covers transitional+turbulent
    A = (2.457 * np.log(1.0 / ((7.0/Re)**0.9 + 0.27*eps_rel)))**16
    B = (37530.0 / Re)**16
    f = 8 * ((8.0/Re)**12 + 1.0/(A+B)**1.5)**(1.0/12.0)
    return f

# ----------------------------------------------------------------------------
# LOOP PRESSURE BALANCE  ->  mass flow
# ----------------------------------------------------------------------------
def buoyancy_head(T_in_C, T_out_C, T_ext_C):
    """Stack driving pressure [Pa] from segmented loop density integral.
    Hot legs use riser-mean and outlet temperatures; cold legs use inlet air
    (downcomer) and outdoor air (external return column)."""
    T_in, T_out, T_ext = (x+273.15 for x in (T_in_C, T_out_C, T_ext_C))
    T_rm = 0.5*(T_in + T_out)                 # riser mean
    rho_in  = ap.rho(T_in)
    rho_out = ap.rho(T_out)
    rho_rm  = ap.rho(T_rm)
    rho_ext = ap.rho(T_ext)
    dP = g * ( rho_ext*H_ATM + rho_in*H_DOWNC
               - rho_rm*H_RISER - rho_out*(H_OPLENUM + H_CHIM) )
    return dP

def loss_head(m_dot, T_in_C, T_out_C):
    """Total loop friction+form loss [Pa] at mass flow m_dot [kg/s]."""
    T_in, T_out = T_in_C+273.15, T_out_C+273.15
    T_rm = 0.5*(T_in+T_out)
    # ---- risers (12 parallel): main resistance ----
    m_r = m_dot / N_RISER
    rho_r = ap.rho(T_rm); mu_r = ap.mu(T_rm)
    V_r = m_r / (rho_r * A_riser)
    Re_r = rho_r * V_r * Dh / mu_r
    f_r = darcy_f(Re_r)
    # form losses: sudden contraction into riser (0.5), expansion out (1.0),
    # 90-deg turns entering/leaving plena (~2 x 0.5), inlet-plenum split (~0.5)
    K_r = 0.5 + 1.0 + 1.0 + 0.5
    dP_riser = (f_r * L_heat/Dh + K_r) * 0.5 * rho_r * V_r**2
    # ---- downcomer (uninsulated, cold air ~T_in) ----
    rho_d = ap.rho(T_in); mu_d = ap.mu(T_in)
    V_d = m_dot / (rho_d * A_DOWNC)
    Re_d = rho_d * V_d * (24*IN) / mu_d
    f_d = darcy_f(Re_d)
    K_d = 0.5 + 0.9 + 1.0           # entrance + 90 elbow + flow conditioner
    dP_downc = (f_d * L_DOWNC/(24*IN) + K_d) * 0.5 * rho_d * V_d**2
    # ---- chimney (dual 24-in, hot air ~T_out) ----
    rho_c = ap.rho(T_out); mu_c = ap.mu(T_out)
    V_c = m_dot / (rho_c * A_CHIM)
    Re_c = rho_c * V_c * (24*IN) / mu_c
    f_c = darcy_f(Re_c)
    K_c = 0.5 + 0.9 + 1.0           # plenum->port entrance + elbow + exit
    dP_chim = (f_c * L_CHIM_EQ/(24*IN) + K_c) * 0.5 * rho_c * V_c**2
    return dP_riser + dP_downc + dP_chim, dict(V_r=V_r, Re_r=Re_r, f_r=f_r,
             dP_riser=dP_riser, dP_downc=dP_downc, dP_chim=dP_chim, V_c=V_c)

# ----------------------------------------------------------------------------
# INTERNAL (gas-side) CONVECTION  ->  riser inner wall temperature
# ----------------------------------------------------------------------------
def h_internal(m_dot, T_m_C):
    """Riser internal convection coefficient [W/m2K] at mean gas temp."""
    T_m = T_m_C + 273.15
    m_r = m_dot / N_RISER
    rho_m = ap.rho(T_m); mu_m = ap.mu(T_m); k_m = ap.k(T_m); Pr_m = ap.Pr(T_m)
    V = m_r / (rho_m * A_riser)
    Re = rho_m * V * Dh / mu_m
    if Re > 3000:
        f = (0.790*np.log(Re) - 1.64)**-2          # Petukhov
        Nu = (f/8)*(Re-1000)*Pr_m / (1 + 12.7*np.sqrt(f/8)*(Pr_m**(2/3)-1))  # Gnielinski
    else:
        Nu = 4.36  # laminar, const heat flux, fully developed
    # entry-length enhancement (L/Dh ~ 98): modest, ~ (1+(Dh/L)^0.7) ~ few %
    Nu *= (1 + (Dh/L_heat)**0.7)
    h = Nu * k_m / Dh
    return h, Re, Nu

# ----------------------------------------------------------------------------
# CAVITY natural convection (enclosed vertical air layer, plate<->riser)
# ----------------------------------------------------------------------------
def h_cavity(T_p_C, T_r_C):
    """Enclosed vertical air-gap convection coefficient [W/m2K].
    Correlation: high-Ra turbulent vertical enclosure Nu = 0.046 Ra_L^(1/3)
    (MacGregor & Emery / Catton, valid Ra_L>~1e6, large aspect ratio),
    referenced to the gap width L and overall (hot-cold) temperature drop."""
    T_p, T_r = T_p_C+273.15, T_r_C+273.15
    T_f = 0.5*(T_p+T_r)
    dT = max(T_p - T_r, 1.0)
    nu_f = ap.nu(T_f); al_f = ap.alpha(T_f); k_f = ap.k(T_f); b = 1.0/T_f
    Ra = g*b*dT*CAV_GAP**3 / (nu_f*al_f)
    if Ra < 1e6:
        Nu = 0.22*(Ra*0.7/(0.2+0.7))**0.28 * (CAV_H/CAV_GAP)**-0.25  # Berkovsky
        Nu = max(Nu, 1.0)
    else:
        Nu = 0.046 * Ra**(1.0/3.0)
    h = Nu * k_f / CAV_GAP
    return h, Ra, Nu

# ----------------------------------------------------------------------------
# COUPLED STEADY-STATE SOLVE
# ----------------------------------------------------------------------------
def solve_steady(Q_air, T_in_C, T_ext_C, wind=0.0, dP_wind=0.0, verbose=False):
    """Solve the coupled loop for given heat-to-air Q_air [W].
    Returns dict of all reported quantities."""
    # Iterate on T_out (hence riser temps -> density -> flow -> Q=m cp dT).
    T_out = T_in_C + 60.0
    for _ in range(100):
        T_m = 0.5*(T_in_C + T_out)
        cp_m = ap.cp_simple(T_m+273.15)
        # ---- flow: balance buoyancy vs losses ----
        dP_b = buoyancy_head(T_in_C, T_out, T_ext_C) + dP_wind
        if dP_b <= 0:
            return None
        def resid(m):
            dl, _ = loss_head(m, T_in_C, T_out)
            return dP_b - dl
        m_dot = brentq(resid, 1e-3, 20.0)
        # ---- energy: update T_out ----
        dT_new = Q_air / (m_dot * cp_m)
        T_out_new = T_in_C + dT_new
        if abs(T_out_new - T_out) < 1e-4:
            T_out = T_out_new; break
        T_out = 0.5*T_out + 0.5*T_out_new
    T_m = 0.5*(T_in_C + T_out)
    dT_air = T_out - T_in_C
    _, lossinfo = loss_head(m_dot, T_in_C, T_out)

    # ---- internal convection -> inner wall temps ----
    h_i, Re_i, Nu_i = h_internal(m_dot, T_m)
    qpp_int = Q_air / A_int                      # mean internal heat flux W/m2
    T_wall_mean = T_m + qpp_int / h_i            # avg inner wall temp
    # midplane (z=3500mm): local air temp (uniform axial heating) + local flux
    T_air_mid = T_in_C + 0.5*dT_air              # z/L ~ 0.5
    T_wall_mid = T_air_mid + qpp_int / h_i       # inner wall, midplane
    # thin steel wall drop (0.188 in, k~50): negligible check
    t_w = 0.188*IN
    dT_wall_cond = qpp_int * t_w / 50.0          # ~ inner->outer
    T_r_out_mid = T_wall_mid + dT_wall_cond      # outer front-face temp, midplane

    # ---- plate temperature & radiation/convection split (cavity side) ----
    # Solve Q_air = Q_rad(T_p,T_r) + Q_convcav(T_p,T_r), with T_r = mean riser
    # outer surface temp. Use mean outer surface temp as radiation sink.
    T_r_mean = T_wall_mean + dT_wall_cond
    R_rad = (1/EPS_P + 1/EPS_R - 1)              # parallel-plate gray, F->1 (reradiating walls)
    def plate_resid(T_p):
        hc, _, _ = h_cavity(T_p, T_r_mean)
        Q_rad = SIGMA*A_PLATE*((T_p+273.15)**4 - (T_r_mean+273.15)**4)/R_rad
        Q_cv  = hc*A_PLATE*(T_p - T_r_mean)
        return Q_rad + Q_cv - Q_air
    lo = T_r_mean + 1e-3
    if plate_resid(lo) >= 0:        # tiny Q: plate essentially at sink temp
        T_p = T_r_mean + max(Q_air,0)/ (SIGMA*A_PLATE*4*(T_r_mean+273.15)**3/R_rad + 1e-9)
    else:
        T_p = brentq(plate_resid, lo, 2000.0)
    hc, Ra_c, Nu_c = h_cavity(T_p, T_r_mean)
    Q_rad = SIGMA*A_PLATE*((T_p+273.15)**4 - (T_r_mean+273.15)**4)/R_rad
    Q_cv  = hc*A_PLATE*(T_p - T_r_mean)
    frac_rad = Q_rad/(Q_rad+Q_cv)

    # plate front-face temp at midplane: local sink hotter by (T_air_mid vs T_m)
    # approximate plate midplane by same balance with local riser outer temp
    def plate_resid_mid(T_p):
        hc2, _, _ = h_cavity(T_p, T_r_out_mid)
        qr = SIGMA*((T_p+273.15)**4-(T_r_out_mid+273.15)**4)/R_rad
        qc = hc2*(T_p - T_r_out_mid)
        return (qr+qc) - qpp_int*(A_int/A_PLATE)  # local plate flux ~ mean
    try:
        T_p_mid = brentq(plate_resid_mid, T_r_out_mid+1, 2000.0)
    except Exception:
        T_p_mid = T_p

    return dict(
        Q_air=Q_air, m_dot=m_dot, m_dot_min=m_dot*60, dT_air=dT_air,
        T_in=T_in_C, T_out=T_out, T_m=T_m, T_ext=T_ext_C,
        dP_buoy=dP_b, **lossinfo,
        h_i=h_i, Re_i=Re_i, Nu_i=Nu_i,
        T_wall_mid=T_wall_mid, T_wall_mean=T_wall_mean, T_r_out_mid=T_r_out_mid,
        T_plate=T_p, T_plate_mid=T_p_mid, h_cav=hc, Ra_cav=Ra_c,
        Q_rad=Q_rad, Q_conv=Q_cv, frac_rad=frac_rad, qpp_int=qpp_int,
    )

def report(r, title=""):
    if r is None:
        print(f"\n=== {title} ===  NO SOLUTION (no net draft)"); return
    print(f"\n=== {title} ===")
    print(f"  Q to air          : {r['Q_air']/1000:6.2f} kW")
    print(f"  Mass flow (loop)  : {r['m_dot']:6.4f} kg/s  = {r['m_dot_min']:6.2f} kg/min")
    print(f"  Riser air dT      : {r['dT_air']:6.1f} C   (T_in {r['T_in']:.0f} -> T_out {r['T_out']:.1f})")
    print(f"  Riser V, Re       : {r['V_r']:.2f} m/s, Re={r['Re_r']:.0f}")
    print(f"  Buoyancy head     : {r['dP_buoy']:6.1f} Pa  (riser {r['dP_riser']:.1f} / downc {r['dP_downc']:.1f} / chim {r['dP_chim']:.1f})")
    print(f"  Internal h_i      : {r['h_i']:6.1f} W/m2K (Nu {r['Nu_i']:.1f})")
    print(f"  Riser wall @mid   : {r['T_wall_mid']:6.1f} C (inner, hot face)")
    print(f"  Plate (front)     : {r['T_plate']:6.1f} C (mean)  {r['T_plate_mid']:6.1f} C (mid)")
    print(f"  Cavity h_conv     : {r['h_cav']:6.2f} W/m2K (Ra {r['Ra_cav']:.2e})")
    print(f"  Q_rad / Q_conv    : {r['Q_rad']/1000:.2f} / {r['Q_conv']/1000:.2f} kW  -> radiative frac = {r['frac_rad']*100:.1f}%")

if __name__ == "__main__":
    # Case 1 baseline: scaled peak duty ~56 kW, inlet 20C, outdoor +2C
    report(solve_steady(56070, 20.0, 2.0), "CASE 1  Q=56.07 kW (scaled peak duty)")
    # Alternative energy accounting: electric 82 kW minus ~12 kW parasitic ~70 kW
    report(solve_steady(70000, 20.0, 2.0), "CASE 1b Q=70 kW (electric 82 - ~12 parasitic)")
    # Normal-operation scaled duty 26.16 kW
    report(solve_steady(26160, 20.0, 2.0), "Normal-op Q=26.16 kW")

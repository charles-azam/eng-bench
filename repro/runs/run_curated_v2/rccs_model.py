"""
NSTF Reactor Cavity Cooling System (RCCS) — first-principles natural-circulation model.

Everything here is built from physics + the geometry/material/condition inputs in ../inputs/.
No facility test data is used.

Physical picture
----------------
  outdoor air  --(downcomer, 24")-->  inlet plenum  --> 12 riser ducts (heated) -->
  outlet plenum --(dual 24" chimney, 19.6 m rise)--> discharge.

Heat path:
  radiant heaters -> 1" heated steel plate (mock vessel, "hot wall", eps~0.78)
    -> across 0.71 m AIR CAVITY by (a) thermal radiation and (b) enclosed natural convection
    -> riser front wall -> conduction through steel -> forced/mixed convection to riser air.
Air warms, becomes buoyant, drives the loop against friction.

Two coupled balances are solved:
  (1) Loop momentum: buoyancy head  ==  sum of friction/form losses  -> gives mass flow m_dot.
  (2) Energy: Q = m_dot*cp*dT ; heat-transfer network gives riser-wall & heated-wall temps.
"""

import numpy as np
from scipy.optimize import brentq

# ----------------------------------------------------------------------------------
# Air properties (ideal gas + power-law fits anchored to inputs/02_materials.md Tbl47)
# ----------------------------------------------------------------------------------
P_ATM = 101325.0        # Pa (barometric ~ near sea level, adjustable)
R_AIR = 287.05          # J/kg-K  (= 8.314/0.02897)
G = 9.80665

def rho_air(T, P=P_ATM):
    """Ideal-gas density, T in K.  Anchored: 1.292 @273K, 0.946 @373K (Table 47)."""
    return P / (R_AIR * T)

def mu_air(T):
    """Dynamic viscosity [Pa.s].  Fit to 17.22e-6@273K, 21.9e-6@373K -> exp 0.770."""
    return 17.22e-6 * (T / 273.15) ** 0.770

def k_air(T):
    """Thermal conductivity [W/m-K]. Fit to 0.024@273K, 0.032@373K -> exp 0.921."""
    return 0.024 * (T / 273.15) ** 0.921

def cp_air(T):
    """Specific heat [J/kg-K]. 1005@273K, 1012@373K; mild rise above (real air ~1030@500K)."""
    return 1005.0 + 0.075 * (T - 273.15)

def Pr_air(T):
    return 0.70   # ~constant 0.70-0.71 over the range (Table 47)

SIGMA = 5.670374419e-8  # Stefan-Boltzmann

# ----------------------------------------------------------------------------------
# Geometry (SI), from inputs/01_geometry.md
# ----------------------------------------------------------------------------------
IN = 0.0254

# Riser ducts (ASTM A500 B, 10"x2"x0.188" wall)
N_RISER = 12
w_out, d_out, t_wall = 2.0*IN, 10.0*IN, 0.188*IN     # 2" wide (faces cavity), 10" deep, wall
w_in  = w_out - 2*t_wall                              # 1.624"
d_in  = d_out - 2*t_wall                              # 9.624"
A_riser_one = w_in * d_in                             # internal flow area, one duct
A_RISER = N_RISER * A_riser_one                       # total internal flow area
P_wet_one = 2*(w_in + d_in)
Dh_RISER = 4*A_riser_one / P_wet_one                  # hydraulic diameter
L_HEAT = 6.82                                         # heated riser length (Table 4)
A_riser_inner = N_RISER * P_wet_one * L_HEAT          # total inner wetted area (heated)
# Front face of riser bank projected toward the plate (the 2"-wide face x length):
A_riser_front = N_RISER * w_out * L_HEAT

# Heated (east) wall = mock vessel
A_PLATE = 10.18            # m^2, heat-transfer area off primary heated plate (§3.3)
A_HEAT_RISER = 8.82        # m^2, "heated riser area" (Table 41) -> use for rad receiver
CAV_GAP = 0.7066           # m, baseline heated-plate <-> riser spacing
CAV_H   = 6.706            # m, cavity height (22 ft)
CAV_W   = 52*IN            # m, cavity width

EPS_PLATE = 0.785          # mill-scale oxidized SAE1020 (measured pre-test 0.78-0.79)
EPS_RISER = 0.80           # A500 steel, mill-scale / oxidized structural steel (assumed)
EPS_SIDE  = 0.20           # cavity sidewalls (Al/insulated), §6.4.3 view-factor assumption

# Downcomer (inlet), 24" dia, uninsulated
D_DC = 24*IN
A_DC = np.pi/4 * D_DC**2
L_DC = 184.5*IN            # equivalent centerline length

# Chimney: dual 24" stacks (parallel), 19.6 m discharge, equivalent length incl. fittings
D_CH = 24*IN
A_CH_one = np.pi/4 * D_CH**2
A_CH = 2 * A_CH_one        # dual chimney -> 0.584 m^2 (matches Table 10)
L_CH_eq = 826.13*IN        # vertical-config equivalent length (Table 8, includes all fittings)

# Loop elevation (Table 56, NSTF baseline): inlet-to-outlet
DZ_LOOP = 20.47            # m
# Inside the loop, the bottom ~1.5 m (inlet plenum up to riser entrance) is still cold air.
L_COLD_ENTRY = 1.5         # m of cold (ambient-T) inside column below the heated riser
H_CHIM_RISE = DZ_LOOP - L_HEAT - L_COLD_ENTRY   # hot rise above heated section (~12.15 m)
# Minor-loss bucket (flow conditioner, plenum expansions/contractions, 5 chimney "loafer"
# butterfly valves partly open, instrument probes) -- physically uncertain, K on chimney V-head.
K_MINOR_LOOP = 4.0
# Effective chimney gas cooling (insulated stack loses a few % of Q) -> hot-column T drop.
DT_CHIM_COOL = 12.0        # K, mean cooldown of the rising column over the chimney

# ----------------------------------------------------------------------------------
# Friction factor
# ----------------------------------------------------------------------------------
def darcy_f(Re, rel_rough=0.0):
    if Re < 2300:
        return 64.0 / max(Re, 1.0)
    # Blasius/smooth turbulent; steel duct roughness small vs D here
    f_smooth = 0.316 * Re ** -0.25
    return f_smooth

# ----------------------------------------------------------------------------------
# (1) LOOP MOMENTUM BALANCE  ->  mass flow rate
# ----------------------------------------------------------------------------------
def buoyancy_head(T_in, T_out, T_amb):
    """
    Driving pressure = g * integral( rho_ambient_outside - rho_inside(z) ) dz  over the loop.
    Inside profile:
      - across heated riser (L_HEAT): T rises linearly T_in -> T_out (rho ~ 1/T)
      - up the chimney rise (H_CHIM_RISE): T ~ T_out (insulated stacks; ~small loss ignored here)
    Outside reference column: ambient air at T_amb over the full DZ_LOOP.
    """
    rho_amb = rho_air(T_amb)
    # integral of rho over the heated riser with linear T (analytic for rho=C/T):
    C = P_ATM / R_AIR
    # integral_0^L C/(T_in + (T_out-T_in)*x/L) dx = C*L/(T_out-T_in)*ln(T_out/T_in)
    if abs(T_out - T_in) > 1e-6:
        int_rho_riser = C * L_HEAT / (T_out - T_in) * np.log(T_out / T_in)
    else:
        int_rho_riser = rho_air(T_in) * L_HEAT
    T_chim = T_out - DT_CHIM_COOL          # slightly cooled rising column (insulated-stack loss)
    int_rho_chim = rho_air(T_chim) * H_CHIM_RISE
    int_rho_cold = rho_air(T_in) * L_COLD_ENTRY   # cold inside column below heated riser
    int_rho_inside = int_rho_riser + int_rho_chim + int_rho_cold
    dP = G * (rho_amb * DZ_LOOP - int_rho_inside)
    return dP

def loss_head(mdot, T_in, T_out, T_amb):
    """Sum of friction + form losses around the loop for a given mdot."""
    T_mean_r = 0.5*(T_in + T_out)
    losses = 0.0
    # -- downcomer (ambient air) --
    rho = rho_air(T_amb); mu = mu_air(T_amb)
    V = mdot/(rho*A_DC); Re = rho*V*D_DC/mu
    f = darcy_f(Re)
    losses += (f*L_DC/D_DC + 0.5) * 0.5*rho*V**2         # +0.5 entrance
    # -- inlet plenum expansion (sudden), lump K~1.0 on downcomer velocity head --
    losses += 1.0 * 0.5*rho*V**2
    # -- riser bank (parallel 12) --
    rho = rho_air(T_mean_r); mu = mu_air(T_mean_r)
    V = mdot/(rho*A_RISER); Re = rho*V*Dh_RISER/mu
    f = darcy_f(Re)
    losses += (f*L_HEAT/Dh_RISER + 0.5 + 1.0) * 0.5*rho*V**2   # entrance 0.5 + exit 1.0
    # -- outlet plenum + chimney (dual) --
    rho = rho_air(T_out); mu = mu_air(T_out)
    V = mdot/(rho*A_CH); Re = rho*V*D_CH/mu
    f = darcy_f(Re)
    losses += (f*L_CH_eq/D_CH + 0.5) * 0.5*rho*V**2      # contraction into chimney
    losses += 1.0 * 0.5*rho*V**2                          # exit KE loss to atmosphere
    losses += K_MINOR_LOOP * 0.5*rho*V**2                 # lumped minor losses (valves, probes)
    return losses

def solve_flow(Q_air, T_amb, P=P_ATM, extra_stack_dP=0.0):
    """
    Solve coupled buoyancy=loss for mass flow.
    Q_air = net heat into the air stream [W]; T_in = ambient (air drawn from outside).
    extra_stack_dP: optional wind-induced assist(+)/oppose(-) at stack, Pa.
    Returns dict.
    """
    global P_ATM
    T_in = T_amb  # air enters at ambient (uninsulated downcomer preheat neglected)
    def residual(mdot):
        cp = cp_air(T_in + 0.0)
        # iterate T_out with cp at mean
        T_out = T_in + Q_air/(mdot*cp_air(T_in))
        for _ in range(5):
            cpm = cp_air(0.5*(T_in+T_out))
            T_out = T_in + Q_air/(mdot*cpm)
        return buoyancy_head(T_in, T_out, T_amb) + extra_stack_dP - loss_head(mdot, T_in, T_out, T_amb)
    mdot = brentq(residual, 1e-3, 5.0, xtol=1e-6)
    cpm = cp_air(T_in + Q_air/(mdot*cp_air(T_in))*0.5)
    T_out = T_in + Q_air/(mdot*cpm)
    for _ in range(5):
        cpm = cp_air(0.5*(T_in+T_out)); T_out = T_in + Q_air/(mdot*cpm)
    return dict(mdot=mdot, T_in=T_in, T_out=T_out, dT=T_out-T_in,
                dP_drive=buoyancy_head(T_in,T_out,T_amb), cp=cpm)

# ----------------------------------------------------------------------------------
# (2) HEAT-TRANSFER NETWORK  ->  riser-wall temp & heated-wall (vessel) temp
#     and radiation/convection split
# ----------------------------------------------------------------------------------
def h_riser_internal(mdot, T_air_mean):
    """Internal convective coefficient in riser ducts (Dittus-Boelter, heating)."""
    rho = rho_air(T_air_mean); mu = mu_air(T_air_mean); k = k_air(T_air_mean); Pr = Pr_air(T_air_mean)
    V = mdot/(rho*A_RISER); Re = rho*V*Dh_RISER/mu
    if Re > 4000:
        Nu = 0.023 * Re**0.8 * Pr**0.4
    elif Re < 2300:
        Nu = 4.36  # laminar, const q''
    else:
        # linear blend
        Nu_t = 0.023*4000**0.8*Pr**0.4
        Nu = 4.36 + (Nu_t-4.36)*(Re-2300)/(4000-2300)
    return Nu*k/Dh_RISER, Re, V

def h_cavity_natconv(T_hot, T_cold):
    """
    Enclosed natural convection in the tall vertical air cavity between heated plate (hot)
    and riser bank (cold). Correlation: MacGregor & Emery / ASHRAE tall-cavity,
    Nu = 0.046 Ra^(1/3) for high Ra (Ra>1e7), based on gap width L, capped for aspect ratio.
    Cite: Incropera, 'Fundamentals of Heat and Mass Transfer' (vertical rectangular cavity).
    """
    T_film = 0.5*(T_hot+T_cold)
    rho = rho_air(T_film); mu = mu_air(T_film); k = k_air(T_film)
    Pr = Pr_air(T_film); beta = 1.0/T_film
    nu = mu/rho; alpha = k/(rho*cp_air(T_film))
    L = CAV_GAP
    Ra = G*beta*abs(T_hot-T_cold)*L**3/(nu*alpha)
    # tall enclosure: use Nu = 0.046 Ra^(1/3) (valid Ra 1e6-1e9, boundary-layer regime)
    if Ra < 1e4:
        Nu = 1.0
    else:
        Nu = 0.046 * Ra**(1.0/3.0)
        # aspect-ratio limited variants (MacGregor-Emery) as sanity bound
    h = Nu*k/L
    return h, Ra, Nu

def radiation_plate_riser(T_plate, T_riser, A1=A_PLATE, A2=A_HEAT_RISER,
                          e1=EPS_PLATE, e2=EPS_RISER):
    """
    Net radiation heat exchange between heated plate (1) and riser bank (2),
    3 remaining cavity walls treated as adiabatic RE-RADIATING (insulated) surfaces.
    Two-surface + reradiating-wall network (Incropera Eq. 13.30):
       q = sigma(T1^4-T2^4) / [ (1-e1)/(e1 A1) + 1/(A1 F12 + [(1/A1 F1R)+(1/A2 F2R)]^-1) + (1-e2)/(e2 A2) ]
    Approximate view factors: plate faces riser bank; treat F12 ~ 0.5 (rest to reradiating walls),
    F1R = 1-F12, F2R by reciprocity/closure.
    """
    F12 = 0.5
    F1R = 1 - F12
    F2R = 1 - (A1/A2)*F12   # closure via reciprocity A1F12=A2F21 -> F21=A1F12/A2; F2R=1-F21
    F2R = max(F2R, 0.05)
    # reradiating parallel path
    denom_R = 1.0/(A1*F1R) + 1.0/(A2*F2R)
    RbarA = A1*F12 + 1.0/denom_R
    Rtot = (1-e1)/(e1*A1) + 1.0/RbarA + (1-e2)/(e2*A2)
    q = SIGMA*(T_plate**4 - T_riser**4)/Rtot
    return q

def solve_thermal(Q_air, flow, verbose=False):
    """
    Given Q_air and the flow solution, find:
      T_riser_wall (mean), T_plate (heated wall / mock vessel), and rad/conv split.
    Energy: all Q_air enters air from riser inner wall (convection).
            Riser wall receives Q_air from cavity = radiation + cavity natural convection.
    """
    T_in, T_out = flow['T_in'], flow['T_out']
    T_air_mean = 0.5*(T_in+T_out)
    # 1) riser inner-wall temperature from internal convection: Q = h_i A_in (Tw - T_air_mean)
    h_i, Re_r, V_r = h_riser_internal(flow['mdot'], T_air_mean)
    T_rw = T_air_mean + Q_air/(h_i*A_riser_inner)   # mean riser wall temp (thin steel, ~isothermal through wall)
    # small conduction drop across 4.78 mm steel wall (k~50): dT=q''*t/k
    q_pp = Q_air/A_riser_inner
    dT_cond = q_pp*t_wall/50.0
    T_rw_front = T_rw + dT_cond  # front (cavity-facing) slightly hotter
    # 2) heated-plate temp: Q_air = Q_rad(T_plate,T_rw_front) + Q_convcavity(T_plate,T_rw_front)
    def res(T_plate):
        q_rad = radiation_plate_riser(T_plate, T_rw_front)
        h_c, Ra, Nu = h_cavity_natconv(T_plate, T_rw_front)
        q_conv = h_c * A_PLATE * (T_plate - T_rw_front)
        return q_rad + q_conv - Q_air
    T_plate = brentq(res, T_rw_front+1.0, T_rw_front+2000.0)
    q_rad = radiation_plate_riser(T_plate, T_rw_front)
    h_c, Ra, Nu = h_cavity_natconv(T_plate, T_rw_front)
    q_conv = h_c*A_PLATE*(T_plate-T_rw_front)
    return dict(T_air_mean=T_air_mean, h_i=h_i, Re_riser=Re_r, V_riser=V_r,
                T_rw=T_rw, T_rw_front=T_rw_front, q_pp=q_pp, dT_cond=dT_cond,
                T_plate=T_plate, q_rad=q_rad, q_conv=q_conv,
                frac_rad=q_rad/(q_rad+q_conv), h_cav=h_c, Ra_cav=Ra, Nu_cav=Nu)

def K2C(T): return T - 273.15

# ----------------------------------------------------------------------------------
# Report helper
# ----------------------------------------------------------------------------------
def full_case(name, Q_air, T_amb_C, P=P_ATM, extra_stack_dP=0.0):
    T_amb = T_amb_C + 273.15
    flow = solve_flow(Q_air, T_amb, P=P, extra_stack_dP=extra_stack_dP)
    th = solve_thermal(Q_air, flow)
    print(f"\n=== {name} :  Q_air={Q_air/1e3:.1f} kW,  T_amb={T_amb_C:.1f} C ===")
    print(f"  mass flow      m_dot = {flow['mdot']:.4f} kg/s")
    print(f"  air dT (riser)       = {flow['dT']:.1f} C   (T_out={K2C(flow['T_out']):.1f} C)")
    print(f"  buoyancy head        = {flow['dP_drive']:.1f} Pa")
    print(f"  riser Re={th['Re_riser']:.0f}  V={th['V_riser']:.2f} m/s  h_i={th['h_i']:.1f} W/m2K")
    print(f"  riser wall Temp      = {K2C(th['T_rw']):.1f} C  (front {K2C(th['T_rw_front']):.1f} C)")
    print(f"  HEATED-WALL (vessel) = {K2C(th['T_plate']):.1f} C")
    print(f"  cavity: Ra={th['Ra_cav']:.2e} Nu={th['Nu_cav']:.1f} h_cav={th['h_cav']:.2f} W/m2K")
    print(f"  q_rad={th['q_rad']/1e3:.1f} kW ({100*th['frac_rad']:.0f}%)  "
          f"q_conv={th['q_conv']/1e3:.1f} kW ({100*(1-th['frac_rad']):.0f}%)")
    return flow, th

if __name__ == "__main__":
    print("Geometry check:")
    print(f"  riser internal area (1 duct)= {A_riser_one*1e4:.2f} cm^2 ; total A_riser={A_RISER:.4f} m^2")
    print(f"  Dh_riser={Dh_RISER*1000:.1f} mm ; A_riser_inner(heated)={A_riser_inner:.2f} m^2")
    print(f"  A_downcomer={A_DC:.4f} m^2 ; A_chimney(dual)={A_CH:.4f} m^2")
    print(f"  A_plate={A_PLATE} m^2 ; A_riser_front={A_riser_front:.2f} m^2")

    # Baseline steady (design duty ~56 kWt into section), winter ~0 C
    full_case("BASELINE peak-duty, winter", 56.0e3, 0.0)
    # Normal steady duty
    full_case("NORMAL duty, winter", 26.16e3, 0.0)
    # Same peak duty, summer
    full_case("BASELINE peak-duty, summer", 56.0e3, 25.0)

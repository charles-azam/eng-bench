"""
rccs_model.py  —  First-principles 1-D natural-circulation model of the
                  ½-scale air-cooled Reactor Cavity Cooling System (RCCS).

Built ONLY from inputs/ (geometry, materials, boundary conditions) plus
first-principles physics and cited standard correlations.  No facility test
data is used.

Physical picture
----------------
Electric heaters drive a steel "mock-vessel" plate.  The plate transfers heat
across an air-filled cavity to a bank of 12 vertical steel riser ducts, mostly
by RADIATION (parallel-plate exchange) with a smaller cavity NATURAL-CONVECTION
contribution.  Heat conducts through the thin riser wall and is carried away by
air flowing UP inside the risers.  The warmed, buoyant air rises through the
outlet plenum and up a chimney to discharge; cool inlet air is drawn down the
downcomer.  With no pump, the loop mass flow is set by the balance

      buoyancy driving head  ==  sum of friction (major+minor) losses.

Governing equations solved self-consistently:
  (1) momentum (loop):   dp_drive(T)  =  dp_friction(mdot, T)
  (2) air energy:        dT = Q_air / (mdot cp),  T_out = T_in + dT
  (3) riser wall:        T_wall = T_m + Q_air/(h_i A_i)
  (4) plate energy:      Q_rad(T_p,T_wall) + Q_convcav(T_p,T_wall) = Q_air

Correlations cited inline (Incropera & DeWitt, "Fundamentals of Heat and Mass
Transfer"; Churchill; Dittus-Boelter; Sutherland).
"""

import numpy as np
from scipy.optimize import brentq

# ----------------------------------------------------------------------------
# Physical constants
# ----------------------------------------------------------------------------
G = 9.81                 # m/s^2
SIGMA = 5.670374419e-8   # W/m^2K^4  Stefan-Boltzmann
R_UNIV = 8.314462        # J/mol/K
P_ATM = 101325.0         # Pa (facility ~180 m elevation; ~99 kPa actual -> use 1 atm, ~2% effect noted)

# ----------------------------------------------------------------------------
# Geometry (from inputs/01_facility_geometry.md)
# ----------------------------------------------------------------------------
IN = 0.0254

# Riser internal cross-section: 9.624 in x 1.624 in
R_A_INT = (9.624*IN) * (1.624*IN)          # 0.010082 m^2 per riser (matches given 0.0101)
R_PERIM = 2.0*((9.624*IN)+(1.624*IN))      # 0.5713 m
R_DH    = 4.0*R_A_INT/R_PERIM              # 0.0706 m (matches given 0.0707)
N_RISER = 12
L_RISER_TOT = 295*IN                       # 7.49 m total
L_HEATED    = 272*IN                       # 6.91 m inside heated cavity
# internal wetted area of one riser over its heated length (for convection):
R_AI_1 = R_PERIM * L_HEATED                # 3.95 m^2

# Heated plate / cavity radiating area (as-built)
A_PLATE = 10.18                            # m^2 (as-built plate area, inputs 01 sec.3)
EPS_PLATE = 0.785                          # measured 0.78-0.79
EPS_RISER = 0.80                           # oxidized structural steel, standard 0.7-0.85 (Incropera table A.11)

# Downcomer (uninsulated 24-in duct)
DC_D = 24*IN
DC_A = np.pi/4*DC_D**2                     # 0.2922 m^2
DC_L = 184.5*IN                            # 4.69 m

# Chimney (one 24-in stack)
CH_D = 24*IN
CH_A_1 = np.pi/4*CH_D**2                   # 0.2922 m^2 per stack
CH_L = (826+470)*IN                        # 32.9 m equivalent (vert+horiz)

# Buoyant heights
H_HEATED = L_HEATED                        # 6.91 m over which air warms in risers
H_DISCHARGE = 19.6                         # m, baseline chimney discharge height
H_ABOVE = H_DISCHARGE - H_HEATED           # 12.7 m of hot column above the heated region

# ----------------------------------------------------------------------------
# Gas properties
# ----------------------------------------------------------------------------
# Air: Sutherland viscosity & conductivity; ideal-gas density; cp weak T-dep.
#   (White, "Viscous Fluid Flow"; Incropera Table A.4)
def air_rho(T, P=P_ATM):        # T in K
    return P/(287.05*T)
def air_mu(T):
    return 1.716e-5*(T/273.15)**1.5*(273.15+110.4)/(T+110.4)
def air_k(T):
    return 0.0241*(T/273.15)**1.5*(273.15+194.0)/(T+194.0)
def air_cp(T):
    # J/kg/K, mild fit valid 250-900 K (Incropera A.4)
    return 1005.0 + 0.05*(T-300.0) + 1.5e-4*(T-300.0)**2
def air_Pr(T):
    return air_mu(T)*air_cp(T)/air_k(T)

# Generic ideal gas (for argon scenario). MW in kg/mol.
def gas_rho(T, MW, P=P_ATM):
    return P*MW/(R_UNIV*T)

# Argon properties (Incropera A.4): approximate
def ar_mu(T):
    return 2.125e-5*(T/300.0)**0.72
def ar_k(T):
    return 0.0177*(T/300.0)**0.73
def ar_cp(T):
    return 520.0
MW_AIR = 0.02897
MW_AR  = 0.039948

# ----------------------------------------------------------------------------
# Friction
# ----------------------------------------------------------------------------
def darcy_f(Re, eps_D=0.0):
    """Darcy friction factor. Laminar 64/Re; turbulent via Haaland (smooth-ish)."""
    if Re < 1e-6:
        return 1e6
    if Re < 2300:
        return 64.0/Re
    # Haaland explicit approximation to Colebrook
    inv = -1.8*np.log10((eps_D/3.7)**1.11 + 6.9/Re)
    f = (1.0/inv)**2
    # blend region ~2300-4000: just use turbulent (conservative)
    return f

# ----------------------------------------------------------------------------
# Loop solver
# ----------------------------------------------------------------------------
def solve_loop(Q_air, T_amb_C, n_open=12, n_chimney=2, gas='air',
               K_riser=1.7, K_plena=3.0, verbose=False):
    """
    Solve the coupled momentum+energy loop.

    Q_air     : heat delivered to the air (W) — electric power minus parasitic loss
    T_amb_C   : inlet/ambient air temperature (deg C) feeding the downcomer
    n_open    : number of open (flowing) riser ducts (of 12)
    n_chimney : number of open chimney stacks (1 or 2)
    gas       : 'air' or 'argon' (fluid filling the loop)
    K_riser   : lumped minor-loss coeff for riser entrance+exit (per riser path)
    K_plena   : lumped minor-loss coeff for plena/downcomer/elbows (loop)

    Returns dict of results.
    """
    T_in = T_amb_C + 273.15
    A_flow_riser = n_open * R_A_INT
    A_flow_chim  = n_chimney * CH_A_1

    if gas == 'air':
        rho_f = lambda T: air_rho(T); mu_f = air_mu; k_f = air_k
        cp_f = air_cp; Pr_f = air_Pr
    else:  # argon
        rho_f = lambda T: gas_rho(T, MW_AR); mu_f = ar_mu; k_f = ar_k
        cp_f = ar_cp; Pr_f = lambda T: ar_mu(T)*ar_cp(T)/ar_k(T)

    def residual(mdot):
        # energy: dT across risers (all Q carried by the open ducts' flow)
        cp_m = cp_f(T_in + 30)  # initial guess for cp
        dT = Q_air/(mdot*cp_m)
        # iterate cp at mean temp
        for _ in range(3):
            T_m = T_in + dT/2.0
            cp_m = cp_f(T_m)
            dT = Q_air/(mdot*cp_m)
        T_out = T_in + dT
        T_m = T_in + dT/2.0

        rho_in  = rho_f(T_in)
        rho_m   = rho_f(T_m)
        rho_out = rho_f(T_out)

        # --- driving head (Boussinesq / column integral) ---
        # cold descending column at rho_in over full height; hot column: risers at
        # rho_m over heated height, then rho_out over remaining height to discharge.
        dp_drive = G*((rho_in-rho_m)*H_HEATED + (rho_in-rho_out)*H_ABOVE)

        # --- friction ---
        # risers (parallel): velocity per open duct
        V_r = mdot/(rho_m*A_flow_riser)
        Re_r = rho_m*V_r*R_DH/mu_f(T_m)
        f_r = darcy_f(Re_r)
        dp_riser = (f_r*L_RISER_TOT/R_DH + K_riser)*0.5*rho_m*V_r**2

        # chimney
        V_c = mdot/(rho_out*A_flow_chim)
        Re_c = rho_out*V_c*CH_D/mu_f(T_out)
        f_c = darcy_f(Re_c)
        dp_chim = (f_c*CH_L/CH_D)*0.5*rho_out*V_c**2

        # downcomer (cold air)
        V_d = mdot/(rho_in*DC_A)
        Re_d = rho_in*V_d*DC_D/mu_f(T_in)
        f_d = darcy_f(Re_d)
        dp_dc = (f_d*DC_L/DC_D)*0.5*rho_in*V_d**2

        # plena + turning minor losses (referenced to riser dynamic head)
        dp_minor = K_plena*0.5*rho_m*V_r**2

        dp_fric = dp_riser + dp_chim + dp_dc + dp_minor
        return dp_drive - dp_fric, dict(dT=dT, T_out=T_out, T_m=T_m, V_r=V_r,
                                        Re_r=Re_r, f_r=f_r, dp_drive=dp_drive,
                                        dp_fric=dp_fric, dp_riser=dp_riser,
                                        dp_chim=dp_chim, dp_dc=dp_dc, dp_minor=dp_minor)

    # bracket mdot
    lo, hi = 1e-3, 5.0
    flo = residual(lo)[0]; fhi = residual(hi)[0]
    if flo*fhi > 0:
        # fallback scan
        ms = np.linspace(lo, hi, 400)
        r = [residual(m)[0] for m in ms]
        sign = np.sign(r)
        idx = np.where(np.diff(sign) != 0)[0]
        if len(idx)==0:
            raise RuntimeError("no root found")
        lo, hi = ms[idx[0]], ms[idx[0]+1]
    mdot = brentq(lambda m: residual(m)[0], lo, hi, xtol=1e-6)
    _, aux = residual(mdot)

    T_m = aux['T_m']; T_out = aux['T_out']; dT = aux['dT']

    # --- riser internal convection: wall temperature ---
    # Only the OPEN ducts carry flow & are actively cooled.
    A_i = n_open * R_AI_1
    V_r = aux['V_r']; Re_r = aux['Re_r']; Pr = Pr_f(T_m)
    if Re_r > 4000:
        # Dittus-Boelter (heating): Nu = 0.023 Re^0.8 Pr^0.4  (Incropera 8.60)
        Nu = 0.023*Re_r**0.8*Pr**0.4
    elif Re_r > 2300:
        # transitional: Gnielinski
        f = (0.790*np.log(Re_r)-1.64)**-2
        Nu = (f/8)*(Re_r-1000)*Pr/(1+12.7*np.sqrt(f/8)*(Pr**(2/3)-1))
    else:
        Nu = 4.36  # laminar, const q'' (Incropera 8.48)
    h_i = Nu*k_f(T_m)/R_DH
    # wall temp at mid-plane driven by local heat flux ~ Q/A_i
    q_flux = Q_air/A_i
    T_wall = T_m + q_flux/h_i     # mean wall; front face hotter (reported separately)

    # --- plate temperature: radiation + cavity natural convection to riser plane ---
    # Effective cold-sink area: open ducts actively cooled span n_open/12 of cavity;
    # blocked ducts float hot and transfer ~0 net -> reduce effective sink area.
    A_sink = A_PLATE * (n_open/12.0)
    # radiation resistance (parallel gray plates)
    def Qrad(Tp):
        return A_sink*SIGMA*(Tp**4 - T_wall**4)/(1/EPS_PLATE + 1/EPS_RISER - 1)
    # cavity natural convection: vertical plate, Churchill-Chu over cavity height
    def h_cav(Tp):
        Tf = 0.5*(Tp+T_wall)
        beta = 1.0/Tf
        nu = air_mu(Tf)/air_rho(Tf)
        al = air_k(Tf)/(air_rho(Tf)*air_cp(Tf))
        Lc = 6.7  # cavity height
        Ra = G*beta*max(Tp-T_wall,1e-3)*Lc**3/(nu*al)
        Pr_ = air_Pr(Tf)
        # Churchill-Chu vertical plate (Incropera 9.26)
        Nu = (0.825 + 0.387*Ra**(1/6)/(1+(0.492/Pr_)**(9/16))**(8/27))**2
        return Nu*air_k(Tf)/Lc
    def Qconv(Tp):
        return h_cav(Tp)*A_sink*(Tp-T_wall)
    def plate_res(Tp):
        return Qrad(Tp)+Qconv(Tp) - Q_air
    Tp = brentq(plate_res, T_wall+1, T_wall+2000)
    q_rad = Qrad(Tp); q_conv = Qconv(Tp)
    rad_frac = q_rad/(q_rad+q_conv)

    res = dict(mdot=mdot, mdot_kgmin=mdot*60, dT=dT, T_in_C=T_in-273.15,
               T_out_C=T_out-273.15, T_m_C=T_m-273.15,
               T_wall_C=T_wall-273.15, T_plate_C=Tp-273.15,
               Re_r=Re_r, V_r=V_r, h_i=h_i, Nu=Nu,
               q_rad=q_rad, q_conv=q_conv, rad_frac=rad_frac,
               dp_drive=aux['dp_drive'], dp_fric=aux['dp_fric'],
               dp_riser=aux['dp_riser'], dp_chim=aux['dp_chim'],
               dp_dc=aux['dp_dc'], dp_minor=aux['dp_minor'],
               n_open=n_open, n_chimney=n_chimney, Q_air=Q_air, gas=gas)
    if verbose:
        for kk,vv in res.items():
            print(f"  {kk:12s} = {vv}")
    return res


if __name__ == "__main__":
    print("=== Baseline sanity check: Case 1, 82 kWe ~ 56 kWt, both chimneys, air ===")
    # assume ~10% parasitic loss -> Q_air ~ 0.9 * electric-equivalent thermal
    r = solve_loop(Q_air=0.90*56070, T_amb_C=20.0, n_open=12, n_chimney=2, gas='air', verbose=True)

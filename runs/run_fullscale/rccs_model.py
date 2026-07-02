"""
Full-scale RCCS natural-circulation model (227-duct HTGR Reactor Cavity Cooling System).

Built from first principles + the sanctioned inputs only. No lookup of the real design's
published performance. General correlations are cited in the calc note.

Physics:
  1) Loop momentum balance: buoyancy head = friction + form losses  (natural circulation)
  2) Energy balance:        Q = m_dot * cp * dT_riser
  3) Heat-transfer chain:   air -> riser inner wall (convection, Dittus-Boelter)
                            riser front face -> plate (two-surface radiation across cavity)
Solved self-consistently by iterating on total mass flow.
"""

import numpy as np
from scipy.optimize import brentq
from CoolProp.CoolProp import PropsSI

# ----------------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------------
g = 9.80665
SIGMA = 5.670374419e-8          # Stefan-Boltzmann
P_ATM = 101325.0                # Pa (task says ~1 atm; facility ~180 m, use 1 atm)
R_air = 287.05

# ----------------------------------------------------------------------------------
# Full-scale geometry (from inputs/01_facility_geometry.md §2, §5)
# ----------------------------------------------------------------------------------
N_DUCT       = 227              # full-scale riser count
L_HEATED     = 13.86            # m, heated riser length (given)
A_HEATED     = 311.2            # m^2, total heated (plate) area (given)

# Duct cross-section: internal 9.624 in x 1.624 in (same at full scale, 1:1)
IN = 0.0254
w_wide  = 9.624 * IN            # 0.24445 m (the 10-in "wide" internal dim)
w_narr  = 1.624 * IN            # 0.04125 m (the 2-in "narrow" internal dim, front face)
A_duct  = w_wide * w_narr       # ~0.01008 m^2 per duct internal flow area
P_wet   = 2*(w_wide + w_narr)   # wetted perimeter
D_h     = 4*A_duct/P_wet        # hydraulic diameter (~0.0706 m)
A_flow_tot = N_DUCT * A_duct

# Riser total flow length full-scale. Half-scale: total riser 7.49 m vs heated 6.82 m.
# Scale heated length by same ratio -> total riser length.
L_RISER_TOT = L_HEATED * (7.49/6.82)   # ~15.2 m of duct friction length

# Effective buoyancy / discharge height (real-plant chimney NOT given -> assumption).
# Anchor to half-scale: discharge 19.6 m with total height 26 m; full total height 55.2 m.
# Scale discharge by total-height ratio: 19.6 * (55.2/26) ~ 41.6 m. Use 40 m baseline,
# sensitivity 30 / 50 m reported separately.
H_DISCHARGE = 40.0             # m, top of hot column above riser inlet (ASSUMPTION)

# Emissivities (inputs/02): plate measured 0.79; riser oxidized steel not reported -> 0.8
EPS_PLATE = 0.79
EPS_RISER = 0.80               # assumed for oxidized structural steel (range 0.7-0.9)

# steel wall
T_WALL_STEEL = 0.188*IN        # riser wall thickness
K_STEEL = 50.0

# ----------------------------------------------------------------------------------
# Air properties via CoolProp (T in degC in, SI out)
# ----------------------------------------------------------------------------------
def air(prop, T_C):
    return PropsSI(prop, 'T', T_C+273.15, 'P', P_ATM, 'Air')

def rho(T_C):  return air('D', T_C)
def mu(T_C):   return air('V', T_C)
def cp(T_C):   return air('C', T_C)
def k_air(T_C):return air('L', T_C)
def Pr(T_C):   return air('Prandtl', T_C)

# ----------------------------------------------------------------------------------
# Loss coefficient model (referenced to riser velocity)
# ----------------------------------------------------------------------------------
def friction_factor(Re):
    # smooth-tube turbulent; add mild roughness margin. Use Petukhov-ish / Blasius blend.
    if Re < 2300:
        return 64.0/max(Re,1.0)
    # Colebrook with modest roughness (galvanized/steel ~0.05 mm)
    eps_rough = 5e-5
    f = 0.02
    for _ in range(40):
        f = (-2.0*np.log10(eps_rough/(3.7*D_h) + 2.51/(Re*np.sqrt(f))))**-2
    return f

# Form losses referenced to riser dynamic head:
#   inlet contraction into duct         K ~ 0.5
#   duct exit into outlet plenum (exp.)  K ~ 1.0
#   plena bends + chimney + discharge KE, lumped at riser velocity ~ 1.0
K_FORM = 0.5 + 1.0 + 1.0

# ----------------------------------------------------------------------------------
# Solve loop for a given power
# ----------------------------------------------------------------------------------
def solve_loop(Q_W, T_in_C=20.0, H_disch=H_DISCHARGE, verbose=False):
    rho_a = rho(T_in_C)         # ambient/cold-leg density

    def residual(mdot):
        # energy balance
        cp_m = cp(T_in_C + 50)  # first guess mean
        dT = Q_W/(mdot*cp_m)
        # refine cp at mean T
        for _ in range(5):
            T_mean = T_in_C + dT/2
            cp_m = cp(T_mean)
            dT = Q_W/(mdot*cp_m)
        T_out = T_in_C + dT
        T_mean = T_in_C + dT/2

        rho_m   = rho(T_mean)
        rho_out = rho(T_out)

        # buoyancy driving head:
        #  over heated riser (density ~ mean) + over hot chimney (density ~ outlet)
        H_chim = H_disch - L_HEATED
        dP_drive = g*((rho_a - rho_m)*L_HEATED + (rho_a - rho_out)*H_chim)

        # riser velocity & losses (evaluate props at mean)
        V = mdot/(N_DUCT*rho_m*A_duct)
        Re = rho_m*V*D_h/mu(T_mean)
        f = friction_factor(Re)
        K_tot = f*L_RISER_TOT/D_h + K_FORM
        dP_loss = 0.5*rho_m*V**2*K_tot

        return dP_drive - dP_loss

    mdot = brentq(residual, 0.3, 100.0, xtol=1e-9, rtol=1e-9)

    # recompute reporting quantities
    cp_m = cp(T_in_C+50); dT = Q_W/(mdot*cp_m)
    for _ in range(6):
        T_mean = T_in_C+dT/2; cp_m = cp(T_mean); dT = Q_W/(mdot*cp_m)
    T_out = T_in_C+dT; T_mean = T_in_C+dT/2
    rho_m = rho(T_mean); rho_out = rho(T_out)
    V = mdot/(N_DUCT*rho_m*A_duct)
    Re = rho_m*V*D_h/mu(T_mean)
    f = friction_factor(Re)
    K_tot = f*L_RISER_TOT/D_h + K_FORM
    H_chim = H_disch - L_HEATED
    dP_drive = g*((rho_a-rho_m)*L_HEATED + (rho_a-rho_out)*H_chim)

    # ---- convective HTC (Dittus-Boelter, heating) ----
    Nu = 0.023*Re**0.8*Pr(T_mean)**0.4
    h  = Nu*k_air(T_mean)/D_h

    # ---- riser wall & plate temps at the PEAK axial location (top, T~T_out) ----
    # perimeter-averaged internal convective flux at peak axial station:
    # uniform axial profile => local flux = mean = Q / total internal wetted area
    A_int_tot = N_DUCT*P_wet*L_HEATED
    q_wet = Q_W/A_int_tot                       # W/m^2 over wetted perimeter
    T_wall_avg = T_out + q_wet/h                # perimeter-averaged inner wall temp at top
    # front face runs hotter: it intercepts most radiation over a small face.
    # peaking factor ~1.5 (bounded; thin high-k tube conducts circumferentially).
    F_PEAK = 1.5
    T_wall_front = T_out + F_PEAK*q_wet/h
    # add tiny conduction drop through wall to outer/front surface:
    q_plate = Q_W/A_HEATED
    dT_cond = q_plate*T_WALL_STEEL/K_STEEL
    T_front_surf = T_wall_front + dT_cond       # outer front surface (radiation-facing)

    # ---- plate temp from two-surface radiation across cavity ----
    # q''_plate = sigma (Tp^4 - Tr^4) / (1/ep + 1/er - 1); Tr = front surface temp
    denom = (1/EPS_PLATE + 1/EPS_RISER - 1)
    Tr_K = T_front_surf + 273.15
    Tp_K = (Tr_K**4 + q_plate*denom/SIGMA)**0.25
    T_plate = Tp_K - 273.15
    # (this neglects the parallel natural-convection path plate->cavity air, so it is a
    #  conservative UPPER bound on plate temperature.)

    return dict(Q_kW=Q_W/1e3, mdot=mdot, dT=dT, T_out=T_out, T_mean=T_mean,
                V=V, Re=Re, f=f, K_tot=K_tot, dP_drive=dP_drive, h=h, Nu=Nu,
                q_plate=q_plate, q_wet=q_wet, T_wall_avg=T_wall_avg,
                T_wall_front=T_wall_front, T_front_surf=T_front_surf, T_plate=T_plate,
                mdot_duct=mdot/N_DUCT)

# ----------------------------------------------------------------------------------
# Radiative fraction of heat removal (front-face energy split), simple estimate
# ----------------------------------------------------------------------------------
def radiative_fraction(res):
    # In the cavity, plate->riser transfer is radiation + cavity natural convection.
    # Radiation q''_rad = q_plate (all of it, in this model). Natural convection in the
    # sealed cavity is a parallel path; estimate its share to report a radiative fraction.
    # Cavity air gap ~0.707 m; treat as vertical enclosure, Nu ~ 0.1-0.3 * Ra^(1/3).
    T_p = res['T_plate']; T_r = res['T_front_surf']
    Tf = 0.5*(T_p+T_r)
    beta = 1/(Tf+273.15)
    Lc = 0.7066
    nu = mu(Tf)/rho(Tf); alpha = k_air(Tf)/(rho(Tf)*cp(Tf))
    Ra = g*beta*(T_p-T_r)*Lc**3/(nu*alpha)
    Nu_c = 0.073*Ra**(1/3)      # tall vertical cavity, turbulent
    h_c = Nu_c*k_air(Tf)/Lc
    q_conv = h_c*(T_p-T_r)
    q_rad  = res['q_plate']     # radiative flux that reaches risers (model basis)
    # total delivered = q_rad + q_conv; but energy is fixed = q_plate. Interpret:
    # fraction of the plate->riser transfer carried by radiation:
    frac = q_rad/(q_rad+q_conv)
    return frac, Ra, h_c, q_conv

if __name__ == '__main__':
    print(f"Geometry: A_duct={A_duct:.5f} m^2  P_wet={P_wet:.4f} m  D_h={D_h:.4f} m")
    print(f"          A_flow_tot={A_flow_tot:.3f} m^2  L_riser={L_RISER_TOT:.2f} m  H_disch={H_DISCHARGE} m")
    print(f"          K_form={K_FORM}")
    print()
    for Q, label in [(700e3,'NORMAL 700 kWt'), (1.5e6,'PEAK 1.5 MWt')]:
        r = solve_loop(Q)
        frac,Ra,hc,qc = radiative_fraction(r)
        print(f"=== {label} ===")
        print(f"  mdot_total   = {r['mdot']:.3f} kg/s  ({r['mdot']*60:.1f} kg/min)")
        print(f"  mdot/duct    = {r['mdot_duct']*1000:.2f} g/s")
        print(f"  riser dT     = {r['dT']:.1f} C   (T_out={r['T_out']:.1f} C, T_mean={r['T_mean']:.1f} C)")
        print(f"  V_riser      = {r['V']:.2f} m/s   Re={r['Re']:.0f}   f={r['f']:.4f}  K_tot={r['K_tot']:.2f}")
        print(f"  dP_drive     = {r['dP_drive']:.1f} Pa")
        print(f"  h (D-B)      = {r['h']:.1f} W/m2K  Nu={r['Nu']:.0f}")
        print(f"  q_plate      = {r['q_plate']:.0f} W/m2   q_wet={r['q_wet']:.0f} W/m2")
        print(f"  T_wall_avg   = {r['T_wall_avg']:.0f} C   T_wall_front(peak)={r['T_wall_front']:.0f} C")
        print(f"  T_PLATE peak = {r['T_plate']:.0f} C")
        print(f"  radiative fraction ~ {frac:.2f}  (Ra_cav={Ra:.2e}, h_conv={hc:.2f}, q_conv={qc:.0f})")
        print()

"""
Passive RCCS (½-scale, air-cooled) natural-circulation model — first principles.

Coupled steady-state solver:
  1. Buoyancy loop momentum balance  -> mass flow rate  m_dot
  2. Air energy balance             -> riser air dT
  3. Internal duct convection       -> riser wall temperature
  4. Cavity radiation + nat. conv.  -> heated-plate temperature and rad/conv split

All geometry & properties from inputs/*.md. Air properties from CoolProp (real air, 1 atm).
Correlations cited inline. No facility test data used.
"""
import numpy as np
from CoolProp.CoolProp import PropsSI

P_ATM = 101325.0        # Pa  (facility ~180 m elevation; near-atmospheric)
g = 9.81
SIGMA = 5.670e-8        # Stefan-Boltzmann

# ---------------------------------------------------------------------------
# Air properties at 1 atm from CoolProp (real air).  T in Kelvin.
# ---------------------------------------------------------------------------
def air(T, P=P_ATM):
    rho = PropsSI('D', 'T', T, 'P', P, 'Air')
    cp  = PropsSI('C', 'T', T, 'P', P, 'Air')
    mu  = PropsSI('V', 'T', T, 'P', P, 'Air')
    k   = PropsSI('L', 'T', T, 'P', P, 'Air')
    Pr  = mu * cp / k
    beta = 1.0 / T          # ideal-gas thermal expansion
    return dict(rho=rho, cp=cp, mu=mu, k=k, Pr=Pr, beta=beta)

# ---------------------------------------------------------------------------
# GEOMETRY  (from inputs/01_facility_geometry.md)
# ---------------------------------------------------------------------------
IN = 0.0254
N_RISER = 12

# Riser internal cross section 9.624 in x 1.624 in
r_w = 9.624 * IN            # internal "wide" dim (depth, faces neighbours) 0.2444 m
r_n = 1.624 * IN            # internal "narrow" dim (front->rear)           0.04125 m
A_flow_1 = r_w * r_n                       # 0.01008 m^2 per duct
P_wet_1  = 2 * (r_w + r_n)                 # internal wetted perimeter 0.5713 m
Dh       = 4 * A_flow_1 / P_wet_1          # 0.0707 m
A_flow   = N_RISER * A_flow_1              # total internal flow area 0.1210 m^2

L_riser_total = 7.49       # m total tube
L_heated      = 6.91       # m inside heated cavity (272 in)
# internal convective area (all 4 walls, air is bounded by full perimeter):
A_int = N_RISER * P_wet_1 * L_heated       # ~47.4 m^2

# Riser OUTER dims (10 in x 2 in), narrow front face 2 in wide:
ro_w = 10.0 * IN
ro_n = 2.0 * IN
# front-face (narrow, line of sight to plate) outer area, all 12 ducts:
A_riser_front = N_RISER * ro_n * L_heated  # 12 * 0.0508 * 6.91 = 4.21 m^2

# Heated plate (mock RPV): spans cavity width 52 in over heated height ~6.7 m
W_cav = 52 * IN                            # 1.321 m
H_cav = 6.7                                # m
A_plate = 8.82                             # m^2 (scaling-line heated area; as-built ~10.18)
L_gap  = 0.7066                            # cavity depth plate-face -> riser front

# Chimney / loop
A_chimney = 0.585        # m^2 (two 24-in ducts)  2*pi/4*0.61^2
D_chimney = 0.61
A_down    = np.pi/4*0.61**2   # single 24-in downcomer 0.292 m^2
H_stack   = 19.6         # m discharge height (baseline)  == effective loop height

# ---------------------------------------------------------------------------
# 1. BUOYANCY LOOP  ->  mass flow for given riser T_in, T_out
# ---------------------------------------------------------------------------
def loop_balance(mdot, T_in, T_out, T_cold):
    """Return dP_buoy - dP_loss  (root -> mass flow). Temps in K."""
    T_r_mean = 0.5*(T_in + T_out)
    a_in   = air(T_in)
    a_out  = air(T_out)
    a_rm   = air(T_r_mean)
    a_cold = air(T_cold)

    # --- Driving buoyancy: cold column (down, rho_cold) vs hot column (riser+chimney) ---
    rho_cold = a_cold['rho']
    # hot column: heated riser (0..L_heated at rho_rm) then chimney (L_heated..H_stack at rho_out)
    dP_buoy = g*( rho_cold*H_stack
                  - a_rm['rho']*L_heated
                  - a_out['rho']*(H_stack - L_heated) )

    # --- Friction + form losses around loop ---
    # Riser
    V_r = mdot/(a_rm['rho']*A_flow)
    Re_r = a_rm['rho']*V_r*Dh/a_rm['mu']
    f_r = friction_factor(Re_r, Dh)
    dP_riser = (f_r*L_riser_total/Dh)*(a_rm['rho']*V_r**2/2)

    # Chimney (insulated, ~T_out); Enerwrap length ~32.9 m equivalent
    V_c = mdot/(a_out['rho']*A_chimney)
    Re_c = a_out['rho']*V_c*D_chimney/a_out['mu']
    f_c = friction_factor(Re_c, D_chimney)
    L_chim = (826+470)*IN
    dP_chim = (f_c*L_chim/D_chimney)*(a_out['rho']*V_c**2/2)

    # Downcomer (uninsulated, cold); equiv length 184.5 in
    V_d = mdot/(rho_cold*A_down)
    Re_d = rho_cold*V_d*0.61/a_cold['mu']
    f_d = friction_factor(Re_d, 0.61)
    dP_down = (f_d*184.5*IN/0.61)*(rho_cold*V_d**2/2)

    # Form losses (engineering estimates, Idelchik/Crane):
    #  downcomer 90deg elbow K~0.9; inlet-plenum expansion ~1.0;
    #  riser sudden contraction entrance ~0.5; riser exit into plenum ~1.0;
    #  outlet plenum + chimney entrance ~1.0; two chimney elbows ~0.9 ea; discharge exit ~1.0
    K_riser_v = 0.5 + 1.0          # on riser velocity
    dP_form_r = K_riser_v*(a_rm['rho']*V_r**2/2)
    K_chim_v  = 1.0 + 2*0.9 + 1.0  # chimney entrance + elbows + discharge
    dP_form_c = K_chim_v*(a_out['rho']*V_c**2/2)
    K_down_v  = 0.9 + 1.0
    dP_form_d = K_down_v*(rho_cold*V_d**2/2)

    dP_loss = dP_riser + dP_chim + dP_down + dP_form_r + dP_form_c + dP_form_d
    return dP_buoy - dP_loss, dict(dP_buoy=dP_buoy, dP_loss=dP_loss, V_r=V_r,
                                    Re_r=Re_r, V_c=V_c, dP_riser=dP_riser,
                                    dP_chim=dP_chim, dP_down=dP_down,
                                    dP_form_r=dP_form_r, dP_form_c=dP_form_c,
                                    dP_form_d=dP_form_d, f_r=f_r)

def friction_factor(Re, D, eps=4.5e-5):
    """Darcy f. Laminar 64/Re; turbulent Colebrook (Haaland explicit)."""
    Re = max(Re, 1.0)
    if Re < 2300:
        return 64.0/Re
    # Haaland
    inv = -1.8*np.log10((eps/D/3.7)**1.111 + 6.9/Re)
    return (1.0/inv)**2

def solve_mdot(T_in, T_out, T_cold):
    from scipy.optimize import brentq
    fL = lambda m: loop_balance(m, T_in, T_out, T_cold)[0]
    # bracket
    m = brentq(fL, 1e-3, 5.0, xtol=1e-6)
    _, info = loop_balance(m, T_in, T_out, T_cold)
    return m, info

# ---------------------------------------------------------------------------
# 2-4. Heat transfer network, coupled
# ---------------------------------------------------------------------------
def internal_h(mdot, T_air_mean, T_wall):
    """Internal forced-convection coefficient inside risers (Dittus-Boelter)."""
    a = air(T_air_mean)
    V = mdot/(a['rho']*A_flow)
    Re = a['rho']*V*Dh/a['mu']
    Pr = a['Pr']
    if Re < 2300:
        Nu = 4.36    # fully-developed, uniform-flux laminar (round-tube analog)
    else:
        # Gnielinski (valid 3000<Re<5e6) — more accurate than Dittus-Boelter
        f = (0.790*np.log(Re)-1.64)**-2
        Nu = (f/8)*(Re-1000)*Pr/(1+12.7*np.sqrt(f/8)*(Pr**(2/3)-1))
    h = Nu*a['k']/Dh
    return h, Re, Nu

def cavity_nat_conv_h(T_p, T_r):
    """Natural convection across the vertical air cavity (plate hot, riser cold).
       Vertical rectangular enclosure, MacGregor & Emery / Catton correlation."""
    T_f = 0.5*(T_p+T_r)
    a = air(T_f)
    dT = abs(T_p - T_r)
    Ra_L = g*a['beta']*dT*L_gap**3/( (a['mu']/a['rho'])*(a['k']/(a['rho']*a['cp'])) )
    H_L = H_cav/L_gap    # ~9.5
    # MacGregor-Emery (1969) vertical cavity, 1e4<Ra<1e7:
    Nu1 = 0.42*Ra_L**0.25*a['Pr']**0.012*H_L**(-0.30)
    # High-Ra boundary-layer regime (Ra>1e7): Nu=0.046 Ra^(1/3)
    Nu2 = 0.046*Ra_L**(1/3)
    Nu = max(Nu1, Nu2, 1.0)
    h = Nu*a['k']/L_gap
    return h, Ra_L, Nu

def radiation_Q(T_p, T_r, eps_p=0.785, eps_r=0.85, A=A_plate):
    """Net radiation plate->riser plane (parallel gray surfaces, adiabatic reradiating sides)."""
    denom = 1/eps_p + 1/eps_r - 1
    return SIGMA*A*(T_p**4 - T_r**4)/denom

def solve_steady(Q_cav, T_cold_C=20.0, T_inlet_C=20.0,
                 eps_p=0.785, eps_r=0.85, verbose=False):
    """
    Q_cav = heat delivered from plate into cavity (W), i.e. carried away by air.
    Returns dict of all state variables.
    Unknowns: T_out (air), T_wall (riser), T_plate. m_dot from loop.
    Iterate.
    """
    T_in = T_inlet_C + 273.15
    T_cold = T_cold_C + 273.15
    # initial guesses
    T_out = T_in + 60
    for it in range(200):
        # (a) mass flow from buoyancy given current T_out
        mdot, loop = solve_mdot(T_in, T_out, T_cold)
        # (b) air temperature rise from energy balance
        T_m_air = 0.5*(T_in+T_out)
        cp = air(T_m_air)['cp']
        dT_air = Q_cav/(mdot*cp)
        T_out_new = T_in + dT_air
        # (c) riser wall temp from internal convection: Q = h_i A_int (Tw - T_m_air)
        T_m_air2 = T_in + 0.5*dT_air
        # iterate wall temp with h depending on Tw weakly
        Tw = T_m_air2 + 40
        for _ in range(30):
            h_i, Re_i, Nu_i = internal_h(mdot, T_m_air2, Tw)
            Tw_new = T_m_air2 + Q_cav/(h_i*A_int)
            if abs(Tw_new-Tw) < 0.01: Tw = Tw_new; break
            Tw = 0.5*Tw+0.5*Tw_new
        # (d) plate temp from cavity heat balance: Q = Q_rad(Tp,Tw_front) + Q_conv,cav(Tp,Tw_front)
        # riser front (radiating) surface ~ wall temp Tw (thin steel ~ isothermal perimeter)
        Tr_front = Tw
        Tp = Tr_front + 100
        for _ in range(60):
            Qr = radiation_Q(Tp, Tr_front, eps_p, eps_r)
            h_c, Ra, Nu_c = cavity_nat_conv_h(Tp, Tr_front)
            Qc = h_c*A_plate*(Tp-Tr_front)
            Qtot = Qr+Qc
            # Newton-ish update on Tp
            dQ = Qtot - Q_cav
            # derivative approx
            dTp = 1.0
            Qr2 = radiation_Q(Tp+dTp, Tr_front, eps_p, eps_r)
            h_c2,_,_ = cavity_nat_conv_h(Tp+dTp, Tr_front)
            Qc2 = h_c2*A_plate*(Tp+dTp-Tr_front)
            deriv = ((Qr2+Qc2)-Qtot)/dTp
            Tp_new = Tp - dQ/deriv
            if abs(Tp_new-Tp) < 0.01: Tp = Tp_new; break
            Tp = Tp_new
        # convergence on T_out
        if abs(T_out_new - T_out) < 0.05:
            T_out = T_out_new
            break
        T_out = 0.5*T_out + 0.5*T_out_new

    Qr = radiation_Q(Tp, Tr_front, eps_p, eps_r)
    h_c, Ra, Nu_c = cavity_nat_conv_h(Tp, Tr_front)
    Qc = h_c*A_plate*(Tp-Tr_front)
    h_i, Re_i, Nu_i = internal_h(mdot, T_m_air2, Tw)
    return dict(mdot=mdot, mdot_kgmin=mdot*60, dT_air=dT_air,
                T_in_C=T_in-273.15, T_out_C=T_out-273.15,
                T_wall_C=Tw-273.15, T_plate_C=Tp-273.15,
                Qr=Qr, Qc=Qc, Q_cav=Q_cav, rad_frac=Qr/(Qr+Qc),
                h_i=h_i, Re_i=Re_i, Nu_i=Nu_i, h_c=h_c, Nu_c=Nu_c, Ra_cav=Ra,
                V_r=loop['V_r'], Re_r=loop['Re_r'], dP_buoy=loop['dP_buoy'],
                dP_loss=loop['dP_loss'], loop=loop, iters=it)

if __name__ == '__main__':
    print("=== Geometry checks ===")
    print(f"Dh={Dh:.4f} m, A_flow_total={A_flow:.4f} m^2, A_int={A_int:.2f} m^2, "
          f"A_riser_front={A_riser_front:.2f} m^2, A_plate={A_plate} m^2")
    print()
    for name, Q in [("Case1 baseline (56 kW to cavity)", 56070),
                    ("Normal duty (26.16 kW)", 26160)]:
        s = solve_steady(Q, T_cold_C=20, T_inlet_C=20)
        print(f"--- {name} ---")
        print(f"  m_dot        = {s['mdot']:.4f} kg/s = {s['mdot_kgmin']:.2f} kg/min")
        print(f"  air dT       = {s['dT_air']:.1f} K  (T_in {s['T_in_C']:.1f} -> T_out {s['T_out_C']:.1f} C)")
        print(f"  riser wall T = {s['T_wall_C']:.1f} C")
        print(f"  plate T      = {s['T_plate_C']:.1f} C")
        print(f"  Q_rad={s['Qr']/1000:.1f} kW  Q_conv,cav={s['Qc']/1000:.1f} kW  rad_frac={s['rad_frac']:.2f}")
        print(f"  h_i={s['h_i']:.1f} W/m2K Re_i={s['Re_i']:.0f} Nu_i={s['Nu_i']:.1f} | "
              f"h_cav={s['h_c']:.2f} Ra_cav={s['Ra_cav']:.2e}")
        print(f"  V_riser={s['V_r']:.3f} m/s Re_riser={s['Re_r']:.0f} | "
              f"dP_buoy={s['dP_buoy']:.2f} Pa  (iters={s['iters']})")
        print()

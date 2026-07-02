"""
Steady-state natural-circulation RCCS model (first principles).

Couples:
  (A) loop momentum balance  : buoyant draft = friction  -> mass flow  m_dot
  (B) coolant energy balance : Q_air = m_dot cp dT        -> riser dT
  (C) cavity heat transfer   : Q_air = Q_rad(Tp,Ts)+Q_conv(Tp,Ts) -> plate temp Tp
  (D) riser wall energy      : Q_air = h_i A_i (Twall-Tair) -> riser wall temp Ts
  (E) parasitic losses       : Q_air = P_e - Q_loss(Tp,Tcav)

Correlations cited inline.
"""
import math
import numpy as np
from scipy.optimize import brentq
import air_props as ap
import geometry as g

SIGMA = 5.670374419e-8   # Stefan-Boltzmann
G = 9.80665

# ------------------------------------------------------------------ friction
def darcy_f(Re, D, eps_r=0.0):
    """Darcy friction factor. Laminar 64/Re; turbulent Haaland (smooth)."""
    if Re < 1.0:
        return 1.0
    if Re < 2300:
        return 64.0 / Re
    # Haaland (1983), smooth duct
    return (-1.8 * math.log10((eps_r/3.7)**1.11 + 6.9/Re))**-2


def friction_dP(m_dot, T_in, T_out):
    """Total loop friction + minor losses [Pa] for whole-loop mass flow m_dot."""
    T_riser = 0.5*(T_in + T_out)
    dP = 0.0
    # --- downcomer (building air ~ T_in) ---
    rho = ap.rho(T_in); V = m_dot/(rho*g.A_down)
    Re = rho*V*g.D_down/ap.mu(T_in)
    f = darcy_f(Re, g.D_down)
    K_down = 0.5 + 0.3 + 0.5   # entrance+conditioner + 90 elbow + fittings
    dP += (f*g.L_down/g.D_down + K_down) * 0.5*rho*V**2
    # --- risers (12 parallel), flow per duct ---
    rho = ap.rho(T_riser); Vr = m_dot/(rho*g.A_riser_tot)
    Re = rho*Vr*g.Dh_riser/ap.mu(T_riser)
    f = darcy_f(Re, g.Dh_riser)
    K_riser = 0.5 + 1.0   # contraction into duct + expansion into outlet plenum
    dP += (f*g.L_riser_total/g.Dh_riser + K_riser) * 0.5*rho*Vr**2
    # --- inlet plenum sudden expansion (downcomer -> plenum) ---
    dP += 1.0 * 0.5*ap.rho(T_in)*(m_dot/(ap.rho(T_in)*g.A_down))**2
    # --- chimney (dual duct) ---
    rho = ap.rho(T_out); Vc = m_dot/(rho*g.A_chim_tot)
    Re = rho*Vc*g.D_chim/ap.mu(T_out)
    f = darcy_f(Re, g.D_chim)
    K_chim = 0.5 + 2*0.9 + 1.0   # contraction + 2 elbows + exit
    dP += (f*g.L_chim/g.D_chim + K_chim) * 0.5*rho*Vc**2
    return dP


def draft_dP(T_in, T_out, T_amb, n=40):
    """Buoyant driving pressure [Pa].
    dP = g * integral_0^H (rho_amb - rho_int(z)) dz  along the flow path,
    plus the assisting downcomer term (building air lighter than outdoor)."""
    rho_o = ap.rho(T_amb)          # outdoor reference column density
    dP = 0.0
    # downcomer descending 0..z_inlet with building air at T_in (assist term)
    dP += G * (rho_o - ap.rho(T_in)) * g.z_inlet
    # risers 0..z_top : T rises linearly T_in -> T_out
    zr = np.linspace(0, g.z_top, n)
    Tr = T_in + (T_out - T_in)*zr/g.z_top
    rho_r = np.array([ap.rho(T) for T in Tr])
    dP += G * np.trapezoid(rho_o - rho_r, zr)
    # outlet plenum + chimney z_top..z_discharge at ~T_out
    H_hot = g.z_discharge - g.z_top
    dP += G * (rho_o - ap.rho(T_out)) * H_hot
    return dP


# ------------------------------------------------------------------ cavity HT
def h_cavity(Tp, Ts):
    """Natural-convection conductance across the vertical plate<->riser gap.
    Vertical rectangular cavity, high Rayleigh (boundary-layer regime):
    Nu_L = 0.046 Ra_L^(1/3)  (ASHRAE / Incropera high-Ra vertical cavity).
    Returns h [W/m2/K] based on gap conductance, dT = Tp-Ts."""
    dT = max(Tp - Ts, 1.0)
    Tf = 0.5*(Tp + Ts)
    L = g.cavity_gap
    Ra = G*ap.beta(Tf)*dT*L**3/(ap.nu(Tf)*ap.alpha(Tf))
    Nu = 0.046 * Ra**(1.0/3.0)
    return Nu*ap.k(Tf)/L, Ra, Nu


def rad_exchange_area():
    """Effective radiation exchange conductance A_bar [m2] for the two-surface
    (plate <-> riser curtain) enclosure with reradiating adiabatic side/back
    walls; F_bar -> 1 (opposing faces of a cavity joined by reradiating walls).
    1/A_bar = (1-ep)/(ep Ap) + 1/(Ap F) + (1-es)/(es As)."""
    Ap, As, F = g.A_plate, g.A_curtain, 1.0
    inv = (1-g.eps_plate)/(g.eps_plate*Ap) + 1.0/(Ap*F) + (1-g.eps_riser)/(g.eps_riser*As)
    return 1.0/inv


A_BAR = rad_exchange_area()


def Q_rad(Tp, Ts):
    return SIGMA * A_BAR * (Tp**4 - Ts**4)


def Q_conv_cav(Tp, Ts):
    h, _, _ = h_cavity(Tp, Ts)
    return h * g.A_curtain * (Tp - Ts)


# ------------------------------------------------------------------ riser wall
def h_internal(m_dot, T_riser):
    """Internal forced/mixed convection coefficient, Gnielinski (1976)."""
    rho = ap.rho(T_riser); mu = ap.mu(T_riser)
    V = m_dot/(rho*g.A_riser_tot)
    Re = rho*V*g.Dh_riser/mu
    Pr = ap.Pr(T_riser); kk = ap.k(T_riser)
    if Re < 2300:
        Nu = 4.36  # laminar, uniform-q, but add entrance; use 4.36 floor
    elif Re < 1e4:
        f = (0.790*math.log(Re)-1.64)**-2
        Nu = (f/8)*(Re-1000)*Pr / (1+12.7*math.sqrt(f/8)*(Pr**(2/3)-1))
    else:
        f = (0.790*math.log(Re)-1.64)**-2
        Nu = (f/8)*(Re-1000)*Pr / (1+12.7*math.sqrt(f/8)*(Pr**(2/3)-1))
    # entrance-length enhancement (L/Dh ~ 98, so fully developed ~ ok)
    return Nu*kk/g.Dh_riser, Re, Nu, V


# ------------------------------------------------------------------ losses
def Q_loss(Tp, Tcav, T_amb):
    """Parasitic conduction losses through insulation (steady)."""
    # back of plate through Duraboard (dominant): plate ~ Tp inner face
    q_back = g.k_dura * g.A_dura * (Tp - T_amb) / g.t_dura
    # N/S/W cavity walls through SuperIsol, inner surface ~ Tcav
    q_wall = g.k_super * g.A_wall_ins * (Tcav - T_amb) / g.t_super
    # add external film resistance (h_ext~10) crudely by lumping: reduce ~15%
    return 0.85*(q_back + q_wall)


# ------------------------------------------------------------------ solver
def solve_steady(P_e, T_in_C=20.0, T_amb_C=2.0, verbose=False, front_bump=None):
    """Solve the coupled steady state. Returns dict of results."""
    T_in = T_in_C + 273.15
    T_amb = T_amb_C + 273.15
    cp0 = ap.cp(T_in)

    f_loss = 0.12  # initial guess for parasitic fraction
    Tp = 600.0; Ts = 420.0; Tcav = 500.0
    for outer in range(40):
        Q_air = P_e*(1.0 - f_loss)
        # inner: solve m_dot & dT s.t. draft=friction and dT=Q/(m cp)
        def residual(m):
            cp_m = ap.cp(T_in + 0.5*Q_air/(m*cp0))
            dT = Q_air/(m*cp_m)
            T_out = T_in + dT
            return draft_dP(T_in, T_out, T_amb) - friction_dP(m, T_in, T_out)
        m_dot = brentq(residual, 0.08, 4.0, xtol=1e-6)
        cp_m = ap.cp(T_in + 0.5*Q_air/(m_dot*cp0))
        dT = Q_air/(m_dot*cp_m)
        T_out = T_in + dT
        T_riser = 0.5*(T_in + T_out)
        T_air_mid = T_in + dT*(g.z_mid/g.z_top)   # air temp at instrumented mid-plane

        # riser wall temp (mean) from internal convection
        h_i, Re_i, Nu_i, V_i = h_internal(m_dot, T_riser)
        # mean wall-air film dT over heated length
        dT_film = Q_air/(h_i*g.A_int_heated)
        Ts_mean = T_riser + dT_film
        # front-face (mid-plane) runs hotter: radiation concentrated on front.
        # local front flux enters wall, spreads by conduction; residual film
        # rise estimated from front-face internal area with fin efficiency.
        # front internal area fraction ~ b_in/perimeter
        frac_front = g.riser_in_b/(g.P_riser_in/1)  # not used directly
        # concentration increment: front receives ~Q_rad; effective local
        # coefficient over full perimeter with fin conduction -> modest bump.
        Ts_front_mid = T_air_mid + dT_film*1.6   # 1.6x mean film (flux concentration)
        if front_bump is not None:
            Ts_front_mid = T_air_mid + dT_film*front_bump
        Ts = Ts_front_mid  # radiation sink temperature = front face

        # plate temp: Q_air = Q_rad(Tp,Ts)+Q_conv(Tp,Ts)
        def res_Tp(T):
            return Q_rad(T, Ts) + Q_conv_cav(T, Ts) - Q_air
        Tp = brentq(res_Tp, Ts+1, 1500.0)

        Qr = Q_rad(Tp, Ts); Qc = Q_conv_cav(Tp, Ts)
        Tcav = 0.5*(Tp + Ts)
        # update losses
        Ql = Q_loss(Tp, Tcav, T_amb)
        f_loss_new = min(max(Ql/P_e, 0.02), 0.5)
        if abs(f_loss_new - f_loss) < 1e-4:
            f_loss = f_loss_new
            break
        f_loss = 0.5*f_loss + 0.5*f_loss_new

    h_cav, Ra_cav, Nu_cav = h_cavity(Tp, Ts)
    res = dict(P_e=P_e, Q_air=Q_air, Q_loss=Ql, f_loss=f_loss,
               m_dot=m_dot, m_dot_min=m_dot*60, dT=dT,
               T_in_C=T_in_C, T_out_C=T_out-273.15, T_amb_C=T_amb_C,
               T_riser_mean_C=T_riser-273.15, T_air_mid_C=T_air_mid-273.15,
               Ts_mean_C=Ts_mean-273.15, Ts_front_mid_C=Ts-273.15,
               Tp_C=Tp-273.15, Tcav_C=Tcav-273.15,
               Q_rad=Qr, Q_conv=Qc, rad_frac=Qr/(Qr+Qc),
               h_i=h_i, Re_i=Re_i, Nu_i=Nu_i, V_riser=V_i,
               h_cav=h_cav, Ra_cav=Ra_cav, A_bar=A_BAR,
               draft=draft_dP(T_in, T_out, T_amb),
               fric=friction_dP(m_dot, T_in, T_out))
    if verbose:
        for kk, vv in res.items():
            print(f"  {kk:16s} = {vv:.4g}" if isinstance(vv,(int,float)) else f"  {kk}={vv}")
    return res


if __name__ == "__main__":
    print("A_bar (radiation exchange conductance) =", round(A_BAR,3), "m2")
    print("\n=== CASE 1: baseline, P_e=82 kW, Tin=20C, Tamb=2C ===")
    r = solve_steady(82_000, 20, 2, verbose=True)

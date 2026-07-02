"""
Case 3 - weather sensitivity: how outdoor air temperature and wind change
natural-circulation performance at the baseline heat load (P_e = 82 kW).

Outdoor T sets the density of the cold reference column (draft ~ rho_o - rho_hot):
colder outdoor -> stronger draft -> more flow -> smaller dT & lower temps.

Wind: a chimney discharging into wind sees a stack-outlet pressure change.
A cross-wind at the discharge creates suction (negative Cp ~ -0.3..-0.6 on a
leeward/around vertical stack) that AIDS the draft; a wind blowing into the
discharge (stagnation, +Cp) OPPOSES it.  We bound both with dP_wind = Cp*0.5*rho*U^2.
"""
import numpy as np
import air_props as ap
import geometry as g
from steady import solve_steady, draft_dP, friction_dP, brentq

def solve_with_wind(P_e, T_amb_C, U_wind=0.0, Cp=-0.4, T_in_C=20.0):
    """Add a wind-induced stack pressure term to the draft and re-solve flow.
    Cp<0 -> suction aids draft (typical for flow over/around a stack top)."""
    T_in = T_in_C+273.15; T_amb = T_amb_C+273.15
    cp0 = ap.cp(T_in)
    # baseline solve to get Q_air/f_loss (losses ~ weakly T_amb dependent)
    base = solve_steady(P_e, T_in_C, T_amb_C)
    Q_air = base['Q_air']
    rho_o = ap.rho(T_amb)
    dP_wind = -Cp*0.5*rho_o*U_wind**2   # Cp<0 => positive assist
    def residual(m):
        cp_m = ap.cp(T_in + 0.5*Q_air/(m*cp0))
        dT = Q_air/(m*cp_m); T_out = T_in+dT
        return (draft_dP(T_in, T_out, T_amb) + dP_wind) - friction_dP(m, T_in, T_out)
    m = brentq(residual, 0.05, 5.0, xtol=1e-6)
    cp_m = ap.cp(T_in + 0.5*Q_air/(m*cp0))
    dT = Q_air/(m*cp_m)
    # recompute wall/plate with the new flow via full solver hack:
    r = solve_steady(P_e, T_in_C, T_amb_C)  # temps ~ set by flow; approx via ratio
    # scale dT and temps by flow ratio relative to no-wind baseline
    return dict(m_dot=m, dT=dT, T_out_C=T_in_C+dT, dP_wind=dP_wind,
                draft=draft_dP(T_in, T_in_C+dT+273.15, T_amb))

if __name__ == "__main__":
    print("=== Case 3a: outdoor temperature sweep (no wind), P_e=82 kW ===")
    print(f"{'Tamb[C]':>8} {'m[kg/s]':>8} {'m[kg/min]':>10} {'dT[C]':>7} "
          f"{'Tout[C]':>8} {'Tplate[C]':>10} {'Tris_f[C]':>10} {'draft[Pa]':>10}")
    base_m = None
    for Tamb in [-18, -10, 0, 2, 10, 24]:
        r = solve_steady(82_000, 20, Tamb)
        if Tamb == 2: base_m = r['m_dot']
        print(f"{Tamb:8.0f} {r['m_dot']:8.3f} {r['m_dot_min']:10.1f} {r['dT']:7.1f} "
              f"{r['T_out_C']:8.1f} {r['Tp_C']:10.1f} {r['Ts_front_mid_C']:10.1f} "
              f"{r['draft']:10.1f}")

    print("\n=== Case 3b: wind sweep at Tamb=2C, P_e=82 kW ===")
    print("(Cp=-0.4 assisting suction at stack top; |dP_wind| bounds effect)")
    print(f"{'U[m/s]':>7} {'dP_wind[Pa]':>12} {'m[kg/s]':>8} {'dT[C]':>7} {'Tout[C]':>8}")
    for U in [0, 2, 4, 6, 8, 11]:
        r = solve_with_wind(82_000, 2, U_wind=U, Cp=-0.4)
        print(f"{U:7.1f} {r['dP_wind']:12.2f} {r['m_dot']:8.3f} {r['dT']:7.1f} {r['T_out_C']:8.1f}")

    print("\n  (adverse wind, Cp=+0.4 stagnation into discharge):")
    for U in [4, 8, 11]:
        r = solve_with_wind(82_000, 2, U_wind=U, Cp=+0.4)
        print(f"{U:7.1f} {r['dP_wind']:12.2f} {r['m_dot']:8.3f} {r['dT']:7.1f} {r['T_out_C']:8.1f}")

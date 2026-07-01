"""
Case 2 -- accident decay-heat transient.

The digitized 10th-order polynomial in inputs/04 is numerically unstable outside
its fit window (peaks at the wrong time, goes negative past ~110 h, missing C10),
so -- as inputs/04 explicitly permits -- we IMPOSE THE NORMALIZED SHAPE:
  normal-op 26.16 kW -> rises to 56.07 kW peak at t=84.85 h -> slow decay.

Question posed: peak temperatures, and does the vessel LEVEL OFF or RUN AWAY?

Method: lumped-capacitance on the steel (plate + risers). At each instant the
air loop is QUASI-STEADY (loop time constant ~ seconds-minutes << 85 h), so the
heat REMOVED is a rising function of plate temperature, Q_rem(T_p) (radiation
~T_p^4 plus cavity convection, with the natural-circulation flow responding).
    C_steel dT_p/dt = Q_in(t) - Q_rem(T_p)
Because dQ_rem/dT_p > 0 (strong T^4 feedback), the system is self-limiting:
the plate tracks the quasi-steady equilibrium and levels off -- no runaway.
"""
import numpy as np
from scipy.optimize import brentq
import airprops as ap
import rccs_model as m

SIGMA = m.SIGMA

# ---- imposed decay-heat (removed) power shape, kW -> W --------------------
def Q_in(t_h):
    """Heat delivered to cavity vs time [h]. Normalized shape per inputs/04."""
    Q0, Qpk, tpk = 26.16, 56.07, 84.85
    if t_h <= tpk:
        # smooth rise (1-cos ramp blended with linear) 26->56
        x = t_h / tpk
        f = 0.5*(1 - np.cos(np.pi*x))        # 0..1 S-curve
        return (Q0 + (Qpk-Q0)*f) * 1000.0
    else:
        # slow exponential-like decay after peak (decay heat falls ~ t^-0.2)
        tau = 120.0
        return (Q0 + (Qpk-Q0)*np.exp(-(t_h-tpk)/tau)) * 1000.0

# ---- quasi-steady heat REMOVED as a function of plate temperature ---------
def Q_removed_of_Tp(T_p_C, T_in_C=20.0, T_ext_C=2.0):
    """For a plate held at T_p, find the self-consistent removed heat.
    Fixed-point: Q -> flow & riser temps -> radiation+conv from plate -> Q'."""
    R_rad = (1/m.EPS_P + 1/m.EPS_R - 1)
    Q = 40000.0
    r = None
    for _ in range(200):
        r = m.solve_steady(Q, T_in_C, T_ext_C)
        if r is None:
            return 0.0, None
        T_r_mean = r['T_wall_mean'] + r['qpp_int']*(0.188*m.IN)/50.0
        hc,_,_ = m.h_cavity(T_p_C, T_r_mean)
        Q_new = (SIGMA*m.A_PLATE*((T_p_C+273.15)**4-(T_r_mean+273.15)**4)/R_rad
                 + hc*m.A_PLATE*(T_p_C - T_r_mean))
        Q_new = min(max(Q_new, 1.0), 300000.0)   # clamp to physical range
        if abs(Q_new-Q) < 5.0:
            Q = Q_new; break
        Q = 0.7*Q + 0.3*Q_new                    # damped fixed point
    return Q, r

def Tp_equilibrium(Q_target, T_in_C=20.0, T_ext_C=2.0):
    """Invert: plate temp whose removed heat equals Q_target (steady)."""
    f = lambda Tp: Q_removed_of_Tp(Tp, T_in_C, T_ext_C)[0] - Q_target
    return brentq(f, 40.0, 800.0)

# ---- lumped steel thermal capacitance -------------------------------------
# Plate: A_plate * 1in steel; Risers: 12 * perimeter*wall*length steel.
RHO_S, C_S = 7850.0, 480.0
m_plate = m.A_PLATE * (1.0*m.IN) * RHO_S
m_riser = m.N_RISER * m.P_wet * (0.188*m.IN) * m.L_heat * RHO_S
C_STEEL = (m_plate + m_riser) * C_S      # J/K (dominant plate)

def run_transient(t_end_h=200.0, dt_h=0.25):
    ts = np.arange(0, t_end_h+dt_h, dt_h)
    Tp = np.zeros_like(ts); Qin = np.zeros_like(ts); Qrem = np.zeros_like(ts)
    Tp[0] = Tp_equilibrium(Q_in(0.0))     # start at equilibrium
    for i in range(1, len(ts)):
        qin = Q_in(ts[i-1])
        qrem, _ = Q_removed_of_Tp(Tp[i-1])
        dTdt = (qin - qrem) / C_STEEL      # K/s
        Tp[i] = Tp[i-1] + dTdt * dt_h*3600.0
        Qin[i-1], Qrem[i-1] = qin, qrem
    Qin[-1] = Q_in(ts[-1]); Qrem[-1] = Q_removed_of_Tp(Tp[-1])[0]
    return ts, Tp, Qin, Qrem

if __name__ == "__main__":
    print(f"Steel thermal capacitance C = {C_STEEL/1e3:.0f} kJ/K "
          f"(plate {m_plate:.0f} kg + risers {m_riser:.0f} kg)")
    # quasi-steady equilibrium plate temp at the 56.07 kW peak:
    Tp_pk = Tp_equilibrium(56070.0)
    print(f"Quasi-steady plate temp at 56.07 kW peak: {Tp_pk:.1f} C")
    # sensitivity of removal to plate temp (self-limiting slope):
    for Tp in [300, 350, 400, 450]:
        q,_ = Q_removed_of_Tp(float(Tp))
        print(f"  T_p={Tp} C -> Q_removed={q/1000:.1f} kW")
    print("\nIntegrating transient...")
    ts, Tp, Qin, Qrem = run_transient()
    ipk = int(np.argmax(Tp))
    # full-scale accident peak instant is t=84.85h; report state near there
    idx85 = int(np.argmin(np.abs(ts-84.85)))
    r_pk = m.solve_steady(Q_in(ts[idx85]), 20.0, 2.0)
    print(f"Peak plate temp {Tp[ipk]:.1f} C at t={ts[ipk]:.1f} h "
          f"(Q_in there {Qin[ipk]/1000:.1f} kW)")
    print(f"At t=84.85h (nominal peak power): T_plate={Tp[idx85]:.1f} C, "
          f"Q_in={Qin[idx85]/1000:.1f} kW, flow={r_pk['m_dot']:.3f} kg/s, "
          f"dT_air={r_pk['dT_air']:.1f} C, wall_mid={r_pk['T_wall_mid']:.1f} C")
    print(f"Plate temp at t=200h (late): {Tp[-1]:.1f} C")
    # save trace
    np.savetxt("transient_trace.csv",
               np.column_stack([ts, Qin/1000, Qrem/1000, Tp]),
               header="t_h, Q_in_kW, Q_removed_kW, T_plate_C", delimiter=",", comments="")
    print("saved transient_trace.csv")

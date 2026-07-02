"""
Accident decay-heat transient + ambient/wind sensitivity for the NSTF RCCS.
Builds on rccs_model.py (first-principles loop + heat-transfer network).
"""
import numpy as np
from rccs_model import (solve_flow, solve_thermal, radiation_plate_riser, h_cavity_natconv,
                        rho_air, cp_air, A_PLATE, K2C, EPS_PLATE, EPS_RISER, SIGMA,
                        h_riser_internal, A_riser_inner, full_case, G)

# ----------------------------------------------------------------------------------
# Decay-power curve (inputs/04_conditions.md §6.4.1). t in MINUTES, Pscale=90.
# ----------------------------------------------------------------------------------
C = [466.531039994, 0.078631095079, 0.000170562320568, -1.28449427566e-7,
     5.09424812301e-11, -1.27606140005e-14, 2.04789514471e-18, -2.08318254453e-22,
     1.29530038954e-26, -4.48601180685e-31]
PSCALE = 90.0

def P_electric(t_min):
    """Programmed ELECTRIC power [W] vs time (min). Poly x Pscale (peaks ~88 kWe)."""
    p = sum(C[i]*t_min**i for i in range(10))
    return p * PSCALE

# The programmed electric peak (~87.7 kWe) delivers ~56.07 kWt to the heated section after
# heater/back-insulation losses (inputs: "2nd ramp to 82 kWe so ~56 kWt reaches section").
ETA_SECTION = 56.07e3 / 87.69e3   # ~0.639

def P_section(t_min):
    """Net thermal power delivered to the cavity/air [W] (peaks ~56 kWt)."""
    return P_electric(t_min) * ETA_SECTION

def scan_decay_curve():
    t = np.linspace(0, 6000, 60001)   # up to 100 h (accident window ~84.85 h)
    Pe = np.array([P_electric(ti) for ti in t])
    Ps = np.array([P_section(ti) for ti in t])
    imax = np.argmax(Pe)
    print("Decay curve:")
    print(f"  electric P(0)= {Pe[0]/1e3:.2f} kWe ; PEAK electric = {Pe[imax]/1e3:.2f} kWe "
          f"at t={t[imax]/60:.1f} h")
    print(f"  section (thermal) peak = {Ps[imax]/1e3:.2f} kWt (eta={ETA_SECTION:.3f})")
    for th in [0,5,10,20,40,60,80,100]:
        print(f"    t={th:3d} h : P_section={P_section(th*60)/1e3:6.2f} kWt")
    return t, Ps, t[imax], Ps[imax]

# ----------------------------------------------------------------------------------
# Quasi-steady transient of the heated-wall (vessel) temperature.
# Lumped capacitance: C dTp/dt = P_in(t) - Q_removed(Tp, flow(t))
#   Q_removed = radiation(Tp->riser) + cavity convection ; riser wall & air from flow soln.
# Steel structural thermal mass (plate ~2000 kg + risers ~2100 kg), cp_steel=490.
# ----------------------------------------------------------------------------------
M_STEEL = 2000 + 2100        # kg (heated plates + riser ducts)
CP_STEEL = 490.0             # J/kg-K
C_THERMAL = M_STEEL*CP_STEEL # J/K

def Q_removed(T_plate, mdot, T_in):
    """Heat removed from the plate at plate temp T_plate given loop flow (W)."""
    # air outlet & mean (energy consistent with what plate delivers is found by iteration
    # outside); here we need riser-wall temp -> depends on Q itself. Use fixed-point on Q.
    Q = 40e3
    for _ in range(30):
        cp = cp_air(T_in+50)
        T_out = T_in + Q/(mdot*cp)
        T_air_mean = 0.5*(T_in+T_out)
        h_i,_,_ = h_riser_internal(mdot, T_air_mean)
        T_rw = T_air_mean + Q/(h_i*A_riser_inner)
        q_rad = radiation_plate_riser(T_plate, T_rw)
        h_c,_,_ = h_cavity_natconv(T_plate, T_rw)
        q_conv = h_c*A_PLATE*(T_plate-T_rw)
        Qnew = q_rad+q_conv
        Q = 0.5*Q+0.5*Qnew
        if abs(Qnew-Q) < 1.0: break
    return Q, q_rad, q_conv, T_rw, T_out

def run_transient(T_amb_C, label, t_end_h=100.0):
    T_amb = T_amb_C+273.15
    dt = 60.0  # s
    n = int(t_end_h*3600/dt)
    Tp = T_amb + 5.0   # start near ambient (sealed zero-flow -> ramp)
    ts, Tps, Ps, Qrs = [], [], [], []
    peakTp = -1e9; peakt = 0
    for k in range(n):
        t_s = k*dt; t_min = t_s/60.0
        P_in = P_section(t_min)
        # quasi-steady loop flow at current power (drives buoyancy); guard low power
        try:
            fl = solve_flow(max(P_in, 2e3), T_amb)
            mdot = fl['mdot']
        except Exception:
            mdot = 0.3
        Q_out, q_rad, q_conv, T_rw, T_out = Q_removed(Tp, mdot, T_amb)
        Tp = Tp + dt*(P_in - Q_out)/C_THERMAL
        if Tp > peakTp: peakTp = Tp; peakt = t_min/60.0
        if k % 60 == 0:
            ts.append(t_min/60); Tps.append(K2C(Tp)); Ps.append(P_in/1e3); Qrs.append(Q_out/1e3)
    ts,Tps,Ps,Qrs = map(np.array,(ts,Tps,Ps,Qrs))
    print(f"\n[{label}] T_amb={T_amb_C} C : PEAK heated-wall T = {K2C(peakTp):.1f} C at t={peakt:.1f} h")
    print("   t[h]  P_sec[kW]  vessel[C]")
    for th in [0,20,40,60,72,73,80,90,100]:
        j = np.argmin(np.abs(ts-th))
        print(f"   {ts[j]:5.1f}   {Ps[j]:6.1f}    {Tps[j]:6.1f}")
    return ts, Tps, Ps, Qrs, K2C(peakTp), peakt

# ----------------------------------------------------------------------------------
# Ambient temperature sensitivity (steady, peak duty 56 kW)
# ----------------------------------------------------------------------------------
def ambient_sweep(Q=56e3):
    print("\nAmbient-temperature sensitivity (Q=56 kW, steady):")
    print("  T_amb[C]  mdot[kg/s]  dT[C]  T_out[C]  riserwall[C]  vessel[C]  rad%")
    rows=[]
    for Ta in [-18, -10, 0, 10, 20, 32]:
        fl = solve_flow(Q, Ta+273.15); th = solve_thermal(Q, fl)
        print(f"   {Ta:5.0f}    {fl['mdot']:.3f}     {fl['dT']:5.1f}  {K2C(fl['T_out']):6.1f}     "
              f"{K2C(th['T_rw']):6.1f}      {K2C(th['T_plate']):6.1f}   {100*th['frac_rad']:.0f}")
        rows.append((Ta, fl['mdot'], fl['dT'], K2C(th['T_plate'])))
    return rows

# ----------------------------------------------------------------------------------
# Wind sensitivity: wind at the stack exit imposes a suction ~ Cp * 1/2 rho_a V^2.
# Assist (draft-augmenting) if it depressurizes the outlet; oppose if it pressurizes inlet.
# ----------------------------------------------------------------------------------
def wind_sweep(Q=56e3, T_amb_C=0.0, Cp=0.5):
    T_amb = T_amb_C+273.15; rho_a = rho_air(T_amb)
    print(f"\nWind sensitivity (Q=56 kW, T_amb={T_amb_C} C, |Cp|={Cp}):")
    print("  Vwind[m/s]  assist_dP[Pa]  mdot(assist)  mdot(oppose)  dT_assist  dT_oppose")
    for V in [0,2,4,6,8,10]:
        dP = Cp*0.5*rho_a*V**2
        fa = solve_flow(Q, T_amb, extra_stack_dP=+dP)
        try:
            fo = solve_flow(Q, T_amb, extra_stack_dP=-dP)
            mo, dto = fo['mdot'], fo['dT']
        except Exception:
            mo, dto = float('nan'), float('nan')
        print(f"   {V:5.0f}      {dP:6.1f}       {fa['mdot']:.3f}        "
              f"{mo:.3f}        {fa['dT']:5.1f}     {dto:5.1f}")

if __name__ == "__main__":
    scan_decay_curve()
    ambient_sweep()
    wind_sweep()
    print("\n--- Transient (accident decay curve), lumped-capacitance vessel wall ---")
    print(f"steel thermal mass C = {C_THERMAL/1e6:.2f} MJ/K ; est. time const ~1-2 h")
    run_transient(10.0, "Run014 winter (~10C avg)")
    run_transient(25.0, "Run018 summer (~25C avg)")

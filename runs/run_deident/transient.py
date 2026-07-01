"""
Case 2 - accident decay-heat transient.
Lumped-capacitance energy balance on the heated plate + mock-vessel steel, with the
RCCS air loop treated quasi-steady (air-loop transit time ~seconds << plate time
constant ~minutes << decay ramp ~tens of hours). Shows whether temperature levels
off or runs away.

Decay power: imposed normalized shape 26 -> 56 kWt, peak at t=84.85 h, then decay,
consistent with inputs/04 (the 10th-order polynomial is only given to C9 and starts
at 42 kW at t=0, inconsistent with the stated 26 kW normal load; we therefore impose
the described normalized shape, which is the sanctioned alternative in the input).
"""
import numpy as np
import rccs, props as pr

T_in = 20+273.15
T_amb = 2+273.15

def decay_power(t_h):
    """Scaled decay-heat power [W] vs half-scale time [h]. 26->56 kW, peak 84.85 h."""
    P0, Ppk = 26.16e3, 56.07e3
    tpk = 84.85
    if t_h <= tpk:
        # smooth rise (raised cosine) from P0 to Ppk
        x = t_h/tpk
        return P0 + (Ppk-P0)*0.5*(1-np.cos(np.pi*x))
    else:
        # gentle exponential-like decline after peak (decay heat falls ~t^-0.2)
        return Ppk*(tpk/t_h)**0.30

# Plate + near-surface steel thermal mass (1-in plate over ~10.18 m2 + heater refractory)
m_plate = 10.18*0.0254*7850         # kg
C_plate = m_plate*480               # J/K
# add ~30% for attached structure/heater backing that follows plate temp
C_TH = 1.30*C_plate
print(f"Plate steel mass={m_plate:.0f} kg, thermal capacitance C={C_TH/1e6:.2f} MJ/K")

def q_out(T_p, Q_guess):
    """Heat removed from plate at plate temp T_p, using quasi-steady loop for that Q."""
    # For the loop we need Q; iterate: given T_p, the removed heat is what the cavity
    # transfers. Solve self-consistently: the flow adjusts to whatever Q crosses.
    # We invert: find Q such that steady(Q) yields this T_p.
    return None

# Quasi-steady map T_p(Q): build interpolation
Qs = np.linspace(10e3, 90e3, 60)
Tps, mdots, Trf = [], [], []
for Q in Qs:
    r = rccs.steady(Q, T_in, T_amb)
    Tps.append(r['T_p']); mdots.append(r['mdot']); Trf.append(r['T_rf_mid'])
Tps=np.array(Tps); mdots=np.array(mdots); Trf=np.array(Trf)

def Tp_of_Q(Q):   return np.interp(Q, Qs, Tps)
def mdot_of_Q(Q): return np.interp(Q, Qs, mdots)
def Trf_of_Q(Q):  return np.interp(Q, Qs, Trf)

# Transient integration: C dT_p/dt = P_in(t) - Q_removed(T_p)
# Q_removed(T_p): invert the steady map (monotonic Tp vs Q)
def Qrem_of_Tp(T_p):
    return np.interp(T_p, Tps, Qs)

dt = 60.0  # s
t_end_h = 160.0
n = int(t_end_h*3600/dt)
T_p = Tp_of_Q(decay_power(0.0))   # start at quasi-steady for initial power
rows=[]
for i in range(n):
    t_h = i*dt/3600.0
    Pin = decay_power(t_h)
    Qrem = Qrem_of_Tp(T_p)
    T_p += dt*(Pin - Qrem)/C_TH
    if i % int(3600/dt) == 0:      # hourly log
        rows.append((t_h, Pin/1e3, T_p-273.15, mdot_of_Q(Pin), Trf_of_Q(Pin)-273.15))

rows=np.array(rows)
imax = np.argmax(rows[:,2])
print("\n t[h]   P[kW]  T_plate[C]  mdot[kg/s]  T_riserfront[C]")
for r in rows[::8]:
    print(f"{r[0]:6.1f} {r[1]:6.2f}   {r[2]:7.1f}   {r[3]:7.3f}    {r[4]:7.1f}")
print(f"\nPEAK plate T = {rows[imax,2]:.1f} C at t={rows[imax,0]:.1f} h "
      f"(P={rows[imax,1]:.1f} kW)")
print(f"Quasi-steady plate T at peak power 56.07 kW = {Tp_of_Q(56.07e3)-273.15:.1f} C")
print(f"Peak mass flow = {mdot_of_Q(56.07e3):.3f} kg/s")
print(f"Peak riser front wall T = {Trf_of_Q(56.07e3)-273.15:.1f} C")

# Runaway test: is dQrem/dTp > dPin/dTp always? Radiative cooling ~T^4 => stable.
print("\nStability: dQremoved/dT_plate (W/K) across range:")
for Q in [26e3, 40e3, 56e3, 70e3]:
    Tp = Tp_of_Q(Q); dTp=2.0
    dQ = (Qrem_of_Tp(Tp+dTp)-Qrem_of_Tp(Tp-dTp))/(2*dTp)
    print(f"  at Q={Q/1e3:.0f}kW, T_p={Tp-273.15:.0f}C : dQ/dT = {dQ:.0f} W/K (>0 => self-limiting)")

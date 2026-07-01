"""
Case 3 - weather sensitivity. Baseline heat load (Q_air=56 kW) with outdoor air
temperature -18..+24 C and wind 0..11 m/s.

Outdoor air is the buoyancy reference AND (facility draws outdoor air) the riser inlet
temperature, so T_in = T_amb here. Wind is modelled as a draft perturbation at the
chimney discharge:  dP_wind = Cp * 0.5 * rho_amb * V_wind^2, Cp~+0.3 (favourable cap /
stack effect). Wind can also oppose the draft (Cp<0) depending on direction; we report
the favourable-assist magnitude and note the sign sensitivity.
"""
import numpy as np
import rccs, props as pr

Q = 56.07e3
Cp_wind = 0.30

def run(T_amb_C, V_wind=0.0):
    T_amb = T_amb_C + 273.15
    dPw = Cp_wind*0.5*pr.rho(T_amb)*V_wind**2
    r = rccs.steady(Q, T_amb, T_amb, dP_wind=dPw)   # inlet = outdoor air
    return r

print("== Temperature sensitivity (no wind), Q=56.07 kW, T_in=T_outdoor ==")
print(" T_out[C]  mdot[kg/s] kg/min  dT[K]  T_plate[C]  T_riserfront[C]  frad[%]")
for Tc in [-18, -10, 0, 2, 10, 20, 24]:
    r = run(Tc, 0.0)
    print(f" {Tc:6.0f}   {r['mdot']:7.3f}  {r['mdot']*60:5.1f}  {r['dT']:5.1f}   "
          f"{r['T_p']-273.15:7.1f}     {r['T_rf_mid']-273.15:7.1f}      {r['frad']*100:4.1f}")

print("\n== Wind sensitivity at T_outdoor = +2 C (favourable assist, Cp=+0.30) ==")
print(" V_wind[m/s]  dP_wind[Pa]  mdot[kg/s]  dT[K]  T_plate[C]")
for V in [0, 2, 4, 6, 8, 11]:
    r = run(2.0, V)
    dPw = Cp_wind*0.5*pr.rho(275.15)*V**2
    print(f" {V:8.1f}   {dPw:8.2f}    {r['mdot']:7.3f}   {r['dT']:5.1f}   {r['T_p']-273.15:6.1f}")

# Summary spans
r_cold = run(-18,0); r_hot = run(24,0)
print(f"\nSpan over outdoor -18..+24 C (no wind):")
print(f"  mdot: {r_cold['mdot']:.3f} -> {r_hot['mdot']:.3f} kg/s "
      f"({100*(r_hot['mdot']/r_cold['mdot']-1):+.0f}%)")
print(f"  T_plate: {r_cold['T_p']-273.15:.0f} -> {r_hot['T_p']-273.15:.0f} C")
r_w0 = run(2,0); r_w11 = run(2,11)
print(f"Wind 0->11 m/s (assist) at +2C: mdot {r_w0['mdot']:.3f}->{r_w11['mdot']:.3f} kg/s "
      f"({100*(r_w11['mdot']/r_w0['mdot']-1):+.0f}%), T_plate {r_w0['T_p']-273.15:.0f}->{r_w11['T_p']-273.15:.0f} C")

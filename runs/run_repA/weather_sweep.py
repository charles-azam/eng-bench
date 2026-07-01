"""
Case 3 -- weather sensitivity. Baseline heat load (Q_air = 56.07 kW) held fixed;
vary outdoor air temperature (-18..+24 C) and wind (0..11 m/s).

Physics:
  * Outdoor T sets the density of the tall EXTERNAL cold column (15.6 m lever arm),
    the strongest term in the stack head. Colder outdoor -> denser column ->
    more draft -> higher mass flow -> lower riser dT and cooler walls/plate.
    (Loop assumed to draw outdoor air, so T_in = T_outdoor; building preheating
    would raise T_in and weaken the trend -- noted as an assumption.)
  * Wind at the stack exit perturbs the draft by a stagnation head ~Cp*0.5*rho*V^2.
    A favorable exit pressure coefficient (aspiration, Cp<0) AUGMENTS draft; an
    unfavorable crosswind/back-pressure REDUCES it. We bound both.
"""
import numpy as np
import airprops as ap
import rccs_model as m

Q = 56070.0

print("=== Outdoor-temperature sweep (no wind), Q = 56.07 kW ===")
print(f"{'T_out[C]':>9}{'m_dot[kg/s]':>12}{'kg/min':>9}{'dT_air[C]':>11}"
      f"{'wall_mid[C]':>12}{'plate[C]':>10}{'radfrac[%]':>11}")
Touts = [-18, -10, -2, 2, 10, 18, 24]
for To in Touts:
    r = m.solve_steady(Q, T_in_C=To, T_ext_C=To)   # loop draws outdoor air
    print(f"{To:>9}{r['m_dot']:>12.3f}{r['m_dot_min']:>9.1f}{r['dT_air']:>11.1f}"
          f"{r['T_wall_mid']:>12.1f}{r['T_plate']:>10.1f}{r['frac_rad']*100:>11.1f}")

print("\n=== Same, but inlet held at building air 20 C (only external column varies) ===")
for To in Touts:
    r = m.solve_steady(Q, T_in_C=20.0, T_ext_C=To)
    print(f"{To:>9}{r['m_dot']:>12.3f}{r['m_dot_min']:>9.1f}{r['dT_air']:>11.1f}"
          f"{r['T_wall_mid']:>12.1f}{r['T_plate']:>10.1f}{r['frac_rad']*100:>11.1f}")

print("\n=== Wind sensitivity at outdoor = +2 C (baseline), Q = 56.07 kW ===")
print("Wind dynamic head 0.5*rho_amb*V^2; Cp=+0.4 aids draft, Cp=-0.4 opposes.")
print(f"{'V[m/s]':>7}{'q_dyn[Pa]':>10}{'m(aid)[kg/s]':>13}{'dT(aid)':>9}"
      f"{'m(opp)[kg/s]':>13}{'dT(opp)':>9}")
rho_amb = ap.rho(2+273.15)
r0 = m.solve_steady(Q, 20.0, 2.0)
for V in [0, 3, 6, 9, 11]:
    qdyn = 0.5*rho_amb*V**2
    Cp = 0.4
    r_aid = m.solve_steady(Q, 20.0, 2.0, dP_wind=+Cp*qdyn)
    r_opp = m.solve_steady(Q, 20.0, 2.0, dP_wind=-Cp*qdyn)
    if r_opp is None:
        print(f"{V:>7}{qdyn:>10.1f}{r_aid['m_dot']:>13.3f}{r_aid['dT_air']:>9.1f}"
              f"{'stall':>13}{'-':>9}")
    else:
        print(f"{V:>7}{qdyn:>10.1f}{r_aid['m_dot']:>13.3f}{r_aid['dT_air']:>9.1f}"
              f"{r_opp['m_dot']:>13.3f}{r_opp['dT_air']:>9.1f}")

print(f"\nBaseline (no wind) draft head = {r0['dP_buoy']:.1f} Pa for scale.")

"""
scenarios.py — Run blind scenarios B1, B2, B3 using rccs_model.solve_loop.

Power convention (stated & justified in the note):
  The scaled THERMAL duty is treated as the heat actually carried away by the
  riser air, Q_air:  normal-op = 26.16 kWt, peak-accident = 56.07 kWt.
  The larger electric power (~42 kWe normal, ~82 kWe peak) exceeds Q_air because
  of parasitic losses through the heater backing and cavity insulation; those
  losses do not reach the coolant air and so are excluded from Q_air.
"""
import numpy as np
from rccs_model import solve_loop

Q_NORMAL = 26160.0   # W  (26.16 kWt scaled normal-operation duty)
Q_PEAK   = 56070.0   # W  (56.07 kWt scaled peak decay-heat duty)

def show(tag, r):
    print(f"\n--- {tag} ---")
    print(f"  mdot        = {r['mdot']:.4f} kg/s  ({r['mdot_kgmin']:.2f} kg/min)")
    print(f"  riser dT    = {r['dT']:.1f} C   (T_in {r['T_in_C']:.1f} -> T_out {r['T_out_C']:.1f})")
    print(f"  T_wall(mid) = {r['T_wall_C']:.1f} C   (mean riser wall; front face higher)")
    print(f"  T_plate     = {r['T_plate_C']:.1f} C")
    print(f"  rad frac    = {r['rad_frac']:.3f}   (Qrad {r['q_rad']/1000:.1f} kW / Qconv {r['q_conv']/1000:.1f} kW)")
    print(f"  Re_riser    = {r['Re_r']:.0f}   V_riser = {r['V_r']:.2f} m/s")
    print(f"  dp_drive    = {r['dp_drive']:.1f} Pa = dp_fric {r['dp_fric']:.1f} Pa")

print("="*70)
print("BASELINE CHECKS")
print("="*70)
show("Case1 baseline: 56 kWt duty, 2 chimneys, T_in=20C",
     solve_loop(Q_PEAK, 20.0, n_open=12, n_chimney=2))
show("Normal 26 kWt, 2 chimneys, T_in=20C",
     solve_loop(Q_NORMAL, 20.0, n_open=12, n_chimney=2))

print("\n"+"="*70)
print("SCENARIO B1 — Partially blocked risers (26 kWt, SINGLE chimney)")
print("="*70)
b1 = {}
for stage, n in [(0,12),(1,10),(2,8),(3,6)]:
    r = solve_loop(Q_NORMAL, 20.0, n_open=n, n_chimney=1)
    b1[stage] = r
    show(f"B1 stage {stage}: {n}/12 ducts open ({100*(12-n)/12:.0f}% blocked)", r)

print("\nB1 summary table (relative to stage 0):")
print(f"{'stage':>6}{'open':>6}{'mdot kg/s':>12}{'dmdot%':>9}{'dT C':>8}{'T_plate C':>11}{'dTplate':>9}")
for stage,n in [(0,12),(1,10),(2,8),(3,6)]:
    r=b1[stage]; r0=b1[0]
    print(f"{stage:>6}{n:>6}{r['mdot']:>12.3f}{100*(r['mdot']/r0['mdot']-1):>9.1f}"
          f"{r['dT']:>8.1f}{r['T_plate_C']:>11.1f}{r['T_plate_C']-r0['T_plate_C']:>9.1f}")

print("\n"+"="*70)
print("SCENARIO B3 — Accident summer vs winter (endpoints)")
print("="*70)
# winter avg 10C, summer avg 25C; assume inlet air tracks ambient.
b3 = {}
for season, Tamb in [('winter',10.0),('summer',25.0)]:
    for load, Q in [('normal',Q_NORMAL),('peak',Q_PEAK)]:
        r = solve_loop(Q, Tamb, n_open=12, n_chimney=2)
        b3[(season,load)] = r
        show(f"B3 {season} ({Tamb:.0f}C) {load} ({Q/1000:.0f} kWt)", r)

print("\nB3 winter->summer change:")
print(f"{'load':>8}{'quantity':>14}{'winter':>10}{'summer':>10}{'abs d':>9}{'pct':>8}")
for load in ['normal','peak']:
    w=b3[('winter',load)]; s=b3[('summer',load)]
    for q,lab,unit in [('mdot','mdot','kg/s'),('T_wall_C','T_wall','C'),
                       ('T_plate_C','T_plate','C'),('dT','riser dT','C')]:
        dv=s[q]-w[q]; pct=100*dv/w[q] if w[q]!=0 else 0
        print(f"{load:>8}{lab:>14}{w[q]:>10.3f}{s[q]:>10.3f}{dv:>9.3f}{pct:>7.1f}%")

"""Sensitivity / scaling cross-checks for the RCCS note."""
import numpy as np
import rccs_model as M

print("="*70)
print("1) SENSITIVITY TO ASSUMED DISCHARGE HEIGHT (buoyancy column)")
print("="*70)
for H in [30.0, 40.0, 50.0]:
    for Q,lab in [(700e3,'700kW'),(1.5e6,'1.5MW')]:
        r = M.solve_loop(Q, H_disch=H)
        print(f"  H={H:4.0f} m  {lab}:  mdot={r['mdot']:6.2f} kg/s  dT={r['dT']:5.1f} C"
              f"  T_plate={r['T_plate']:5.0f} C")
    print()

print("="*70)
print("2) SENSITIVITY OF PLATE TEMP TO RISER EMISSIVITY (0.7 / 0.8 / 0.9)")
print("="*70)
import CoolProp.CoolProp as CP
def plate_temp_with_eps(Q, eps_r):
    r = M.solve_loop(Q)
    denom = (1/M.EPS_PLATE + 1/eps_r - 1)
    Tr_K = r['T_front_surf']+273.15
    Tp = (Tr_K**4 + r['q_plate']*denom/M.SIGMA)**0.25 - 273.15
    return Tp
for Q,lab in [(700e3,'700kW'),(1.5e6,'1.5MW')]:
    row = "  ".join(f"eps={e}:{plate_temp_with_eps(Q,e):4.0f}C" for e in (0.7,0.8,0.9))
    print(f"  {lab}: {row}")
print()

print("="*70)
print("3) HALF-SCALE FACILITY PREDICTION (same solver, scaled geometry)")
print("   to verify the scaling mapping to full scale")
print("="*70)
# monkey-patch geometry to half-scale, then restore
save = dict(N_DUCT=M.N_DUCT, L_HEATED=M.L_HEATED, A_HEATED=M.A_HEATED,
            L_RISER_TOT=M.L_RISER_TOT, H_DISCHARGE=M.H_DISCHARGE)
M.N_DUCT=12; M.L_HEATED=6.82; M.A_HEATED=8.82
M.L_RISER_TOT=7.49; M.H_DISCHARGE=19.6
for Q,lab in [(26.16e3,'26.16kW (norm)'),(56.07e3,'56.07kW (peak)')]:
    r = M.solve_loop(Q, H_disch=19.6)
    print(f"  {lab}: mdot={r['mdot']:6.3f} kg/s ({r['mdot']*60:5.1f} kg/min)"
          f"  dT={r['dT']:5.1f} C  V={r['V']:.2f} m/s  Re={r['Re']:.0f}"
          f"  T_plate={r['T_plate']:.0f} C")
# restore
M.N_DUCT=save['N_DUCT']; M.L_HEATED=save['L_HEATED']; M.A_HEATED=save['A_HEATED']
M.L_RISER_TOT=save['L_RISER_TOT']; M.H_DISCHARGE=save['H_DISCHARGE']

print()
print("  Full-scale for comparison (per-duct velocity & Re):")
for Q,lab in [(700e3,'700kW'),(1.5e6,'1.5MW')]:
    r = M.solve_loop(Q)
    print(f"  {lab}: V={r['V']:.2f} m/s  Re={r['Re']:.0f}  mdot/duct={r['mdot_duct']*1000:.1f} g/s")

print()
print("  --> velocity ratio (half/full) and Re ratio show whether sqrt(l_R)=0.707 holds")

print()
print("="*70)
print("4) WEATHER SENSITIVITY (ambient T) at 1.5 MW, full scale")
print("="*70)
for Ta in [-18.0, 0.0, 20.0, 24.0]:
    r = M.solve_loop(1.5e6, T_in_C=Ta)
    print(f"  T_amb={Ta:6.1f} C:  mdot={r['mdot']:6.2f} kg/s  dT={r['dT']:5.1f} C"
          f"  T_out={r['T_out']:5.1f} C  T_plate={r['T_plate']:5.0f} C")

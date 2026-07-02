"""Sensitivity studies + figures for the calculation note."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rccs_model import solve_steady
from rccs_cases import removal_curve, transient, decay_power_W, front_face_delta

print("=== Sensitivity: riser emissivity eps_r (Q=56 kW) ===")
for er in [0.6, 0.7, 0.8, 0.85, 0.9]:
    s = solve_steady(56070, eps_r=er)
    print(f"  eps_r={er:.2f}: plate={s['T_plate_C']:.0f}C wall={s['T_wall_C']:.0f}C "
          f"rad_frac={s['rad_frac']:.2f} mdot={s['mdot']:.3f}")

print("\n=== Sensitivity: delivered power (parasitic-loss assumption) ===")
for Q in [50000, 56070, 62000, 72000]:
    s = solve_steady(Q)
    print(f"  Q_cav={Q/1000:.0f}kW: plate={s['T_plate_C']:.0f}C wall={s['T_wall_C']:.0f}C "
          f"mdot={s['mdot']:.3f} dT={s['dT_air']:.0f}K")

print("\n=== Sensitivity: plate emissivity eps_p (0.78-0.79 measured) ===")
for ep in [0.70, 0.78, 0.79, 0.90]:
    s = solve_steady(56070, eps_p=ep)
    print(f"  eps_p={ep:.2f}: plate={s['T_plate_C']:.0f}C rad_frac={s['rad_frac']:.2f}")

# ---- Figures ----
fig, ax = plt.subplots(1,3, figsize=(15,4.2))

# (1) self-limiting removal curve
Qs, Tp = removal_curve()
ax[0].plot(Tp, Qs/1000, 'o-')
ax[0].axhline(56.07, color='r', ls='--', label='peak accident duty 56 kW')
ax[0].axhline(26.16, color='g', ls=':', label='normal duty 26 kW')
ax[0].set_xlabel('Plate temperature (°C)'); ax[0].set_ylabel('Passive heat removal (kW)')
ax[0].set_title('Self-limiting: removal rises with plate T\n(finite crossing ⇒ levels off)')
ax[0].legend(); ax[0].grid(alpha=0.3)

# (2) transient
C_th, ts, Tps, Pin = transient()
ax2 = ax[1]; ax2b = ax2.twinx()
ax2.plot(ts, Tps, 'b-', label='plate T')
ax2b.plot(ts, np.array(Pin)/1000, 'r--', label='decay power')
ax2.axvline(84.85, color='k', ls=':', alpha=0.5)
ax2.set_xlabel('time (h)'); ax2.set_ylabel('plate T (°C)', color='b')
ax2b.set_ylabel('power (kW)', color='r')
ax2.set_title('Accident transient (quasi-steady): peak %.0f°C @ %.0f h'%(Tps.max(), ts[np.argmax(Tps)]))
ax2.grid(alpha=0.3)

# (3) weather sensitivity
Tamb = np.array([-18,-10,0,2,10,20,24]); md=[]; plate=[]; wall=[]
for Tc in Tamb:
    s = solve_steady(56070, T_cold_C=float(Tc), T_inlet_C=float(Tc))
    md.append(s['mdot_kgmin']); plate.append(s['T_plate_C']); wall.append(s['T_wall_C'])
ax3=ax[2]; ax3b=ax3.twinx()
ax3.plot(Tamb, md, 'g-o', label='mass flow')
ax3b.plot(Tamb, plate, 'm--s', label='plate T')
ax3b.plot(Tamb, wall, 'c--^', label='riser wall T')
ax3.set_xlabel('outdoor/inlet air T (°C)'); ax3.set_ylabel('mass flow (kg/min)', color='g')
ax3b.set_ylabel('temperature (°C)', color='m')
ax3.set_title('Weather sensitivity (56 kW)')
ax3.grid(alpha=0.3)
lines=[ax3.get_lines()[0]]+ax3b.get_lines(); ax3.legend(lines,[l.get_label() for l in lines], loc='center right')

plt.tight_layout(); plt.savefig('rccs_results.png', dpi=110)
print("\nsaved rccs_results.png")

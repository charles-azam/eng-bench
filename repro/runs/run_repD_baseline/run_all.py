"""Run all cases, dump a consolidated results file, and make summary figures."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from steady import solve_steady, A_BAR
from transient import power_curve_scaled
from weather import solve_with_wind

out = {}

# ---- Case 1 baseline ----
c1 = solve_steady(82_000, 20, 2)
out["case1_baseline"] = c1

# ---- Case 2 transient trace ----
ts = np.linspace(0, 140, 57)
trace = [(t, power_curve_scaled(t)) for t in ts]
c2 = []
for t, P in trace:
    r = solve_steady(P, 20, 2)
    c2.append(dict(t_h=t, P_kW=P/1e3, m_dot=r['m_dot'], dT=r['dT'],
                   Tp_C=r['Tp_C'], Ts_front_C=r['Ts_front_mid_C'],
                   rad_frac=r['rad_frac']))
out["case2_peak"] = max(c2, key=lambda d: d['Tp_C'])

# ---- Case 2 stability (power sweep) ----
sweep = []
for P in [26, 40, 56, 82, 120, 160, 220]:
    r = solve_steady(P*1e3, 20, 2)
    sweep.append(dict(P_kW=P, Tp_C=r['Tp_C'], Qrad_kW=r['Q_rad']/1e3,
                      Qconv_kW=r['Q_conv']/1e3, rad_frac=r['rad_frac']))
out["power_sweep"] = sweep

# ---- Case 3 weather ----
weather = []
for Tamb in [-18, -10, 0, 2, 10, 24]:
    r = solve_steady(82_000, 20, Tamb)
    weather.append(dict(Tamb_C=Tamb, m_dot=r['m_dot'], m_min=r['m_dot_min'],
                        dT=r['dT'], Tout_C=r['T_out_C'], Tp_C=r['Tp_C'],
                        Ts_front_C=r['Ts_front_mid_C'], draft=r['draft']))
out["weather_T"] = weather

# ---- print + save ----
def show(d):
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}
print("A_bar =", round(A_BAR, 3))
print("\nCASE 1 baseline:"); [print(f"  {k}={round(v,3) if isinstance(v,float) else v}") for k, v in c1.items()]
print("\nCASE 2 peak:", show(out["case2_peak"]))
print("\nPower sweep:"); [print("  ", show(s)) for s in sweep]
print("\nWeather:"); [print("  ", show(w)) for w in weather]

with open("results.json", "w") as f:
    json.dump({k: (v if not isinstance(v, dict) else show(v)) for k, v in out.items()},
              f, indent=2, default=float)

# ---- figures ----
fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
tt = [d['t_h'] for d in c2]
ax[0].plot(tt, [d['P_kW'] for d in c2], 'k--', label='power P(t)')
ax[0].plot(tt, [d['Tp_C'] for d in c2], 'r-', label='plate T')
ax[0].plot(tt, [d['Ts_front_C'] for d in c2], 'b-', label='riser front T')
ax[0].axhline(550, color='gray', ls=':', label='safe limit ~550C')
ax[0].set_xlabel('time [h]'); ax[0].set_ylabel('kW  /  degC')
ax[0].set_title('Case 2: decay-heat transient (levels off)'); ax[0].legend(fontsize=8)

Ps = [s['P_kW'] for s in sweep]
ax[1].plot(Ps, [s['Tp_C'] for s in sweep], 'ro-', label='plate T (steady)')
ax[1].plot(Ps, [s['Qrad_kW'] for s in sweep], 'b^-', label='Q_rad')
ax[1].plot(Ps, [s['Qconv_kW'] for s in sweep], 'gs-', label='Q_conv')
ax[1].set_xlabel('power [kW]'); ax[1].set_ylabel('degC  /  kW')
ax[1].set_title('Passive stability: monotonic, no runaway'); ax[1].legend(fontsize=8)

Ta = [w['Tamb_C'] for w in weather]
ax2b = ax[2].twinx()
ax[2].plot(Ta, [w['m_min'] for w in weather], 'bo-', label='mass flow')
ax2b.plot(Ta, [w['dT'] for w in weather], 'rs-', label='riser dT')
ax2b.plot(Ta, [w['Tp_C'] for w in weather], 'k^-', label='plate T')
ax[2].set_xlabel('outdoor T [C]'); ax[2].set_ylabel('mass flow [kg/min]', color='b')
ax2b.set_ylabel('dT / plate T [C]')
ax[2].set_title('Case 3: weather sensitivity')
ax[2].legend(loc='upper right', fontsize=8); ax2b.legend(loc='center right', fontsize=8)
plt.tight_layout(); plt.savefig("summary_figures.png", dpi=110)
print("\nSaved results.json and summary_figures.png")

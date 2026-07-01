"""Generate figures for the calculation note."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import rccs_model as m
import accident_transient as tr

# ---- Fig 1: accident transient ----
ts, Tp, Qin, Qrem = tr.run_transient()
fig, ax1 = plt.subplots(figsize=(7,4.2))
ax1.plot(ts, Tp, 'r-', lw=2, label='Plate temp (transient, tracks quasi-steady)')
ax1.axhline(540, color='k', ls=':', lw=1)
ax1.text(5, 548, 'steel strength-loss onset ~540 C', fontsize=8)
ax1.set_xlabel('Time [h, half-scale]'); ax1.set_ylabel('Plate temperature [C]', color='r')
ax1.set_ylim(0, 600); ax1.tick_params(axis='y', labelcolor='r')
ax2 = ax1.twinx()
ax2.plot(ts, Qin, 'b-', lw=1.2, label='Heat input')
ax2.plot(ts, Qrem, 'g-', lw=1, alpha=0.6, label='Heat removed')
ax2.set_ylabel('Power [kW]', color='b'); ax2.set_ylim(0, 120); ax2.tick_params(axis='y', labelcolor='b')
ax1.axvline(84.85, color='gray', ls='--', lw=0.8); ax1.text(86, 30, 't=84.85 h peak', fontsize=8)
ax1.legend(loc='center right', fontsize=8); ax1.set_title('Case 2: accident decay-heat transient -- self-limiting')
fig.tight_layout(); fig.savefig('fig_transient.png', dpi=110)

# ---- Fig 2: weather sweep ----
Q=56070.0
Tos = np.linspace(-18,24,15)
md=[]; dT=[]; Tpl=[]
for To in Tos:
    r=m.solve_steady(Q, To, To)
    md.append(r['m_dot']); dT.append(r['dT_air']); Tpl.append(r['T_plate'])
fig,ax=plt.subplots(1,2,figsize=(9,3.8))
ax[0].plot(Tos, md,'o-'); ax[0].set_xlabel('Outdoor air T [C]'); ax[0].set_ylabel('Loop mass flow [kg/s]')
ax[0].set_title('Flow vs outdoor T'); ax[0].grid(alpha=0.3)
ax[1].plot(Tos, dT,'s-',label='riser dT'); ax[1].plot(Tos, Tpl,'^-',label='plate T')
ax[1].set_xlabel('Outdoor air T [C]'); ax[1].set_ylabel('Temperature [C]'); ax[1].legend(); ax[1].grid(alpha=0.3)
ax[1].set_title('Temperatures vs outdoor T')
fig.tight_layout(); fig.savefig('fig_weather.png', dpi=110)
print("saved fig_transient.png, fig_weather.png")

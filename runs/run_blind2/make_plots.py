"""Generate summary figures for the blind-cases note."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rccs_model import solve_loop

Q_NORMAL, Q_PEAK = 26160.0, 56070.0

# ---- B1 ----
stages=[0,1,2,3]; nopen=[12,10,8,6]; blocked=[0,16.7,33.3,50]
b1=[solve_loop(Q_NORMAL,20.0,n_open=n,n_chimney=1) for n in nopen]
mdot=[r['mdot'] for r in b1]; dT=[r['dT'] for r in b1]; Tp=[r['T_plate_C'] for r in b1]; Tw=[r['T_wall_C'] for r in b1]

fig,ax=plt.subplots(1,3,figsize=(13,4))
ax[0].plot(blocked,[m/mdot[0]*100 for m in mdot],'o-',color='#2b6cb0')
ax[0].set_xlabel('% risers blocked'); ax[0].set_ylabel('mass flow (% of reference)'); ax[0].set_title('B1: loop mass flow'); ax[0].grid(alpha=.3)
ax[1].plot(blocked,dT,'s-',color='#c05621'); ax[1].set_xlabel('% risers blocked'); ax[1].set_ylabel('riser air dT (C)'); ax[1].set_title('B1: air temperature rise'); ax[1].grid(alpha=.3)
ax[2].plot(blocked,Tp,'^-',color='#9b2c2c',label='plate'); ax[2].plot(blocked,Tw,'v-',color='#2f855a',label='riser wall')
ax[2].set_xlabel('% risers blocked'); ax[2].set_ylabel('temperature (C)'); ax[2].set_title('B1: plate & wall temp'); ax[2].legend(); ax[2].grid(alpha=.3)
plt.tight_layout(); plt.savefig('fig_B1_blockage.png',dpi=110); plt.close()

# ---- B3 ----
seasons={'winter':10.0,'summer':25.0}
loads={'normal':Q_NORMAL,'peak':Q_PEAK}
res={(s,l):solve_loop(q,T,n_open=12,n_chimney=2) for s,T in seasons.items() for l,q in loads.items()}
fig,ax=plt.subplots(1,3,figsize=(13,4))
x=np.arange(2); w=0.35
for i,(q,lab) in enumerate([('mdot','mass flow (kg/s)'),('T_wall_C','riser wall T (C)'),('T_plate_C','plate T (C)')]):
    win=[res[('winter',l)][q] for l in ['normal','peak']]
    sum_=[res[('summer',l)][q] for l in ['normal','peak']]
    ax[i].bar(x-w/2,win,w,label='winter 10C',color='#3182ce')
    ax[i].bar(x+w/2,sum_,w,label='summer 25C',color='#dd6b20')
    ax[i].set_xticks(x); ax[i].set_xticklabels(['normal\n26kWt','peak\n56kWt']); ax[i].set_ylabel(lab); ax[i].grid(alpha=.3,axis='y')
    ax[i].legend(fontsize=8)
ax[0].set_title('B3: mass flow'); ax[1].set_title('B3: riser wall temp'); ax[2].set_title('B3: plate temp')
plt.tight_layout(); plt.savefig('fig_B3_weather.png',dpi=110); plt.close()

# ---- B2 buoyancy criterion ----
from rccs_model import air_rho, gas_rho, MW_AR, MW_AIR
T=np.linspace(293,600,100)
fig,ax=plt.subplots(figsize=(6,4))
ax.plot(T-273.15,[gas_rho(t,MW_AR) for t in T],label='argon in riser',color='#805ad5')
ax.axhline(air_rho(293.15),ls='--',color='#3182ce',label='cold inlet air (20C)')
ax.axvline(131.1,ls=':',color='k'); ax.text(133,1.4,'buoyancy-neutral\n131C',fontsize=8)
ax.set_xlabel('riser gas temperature (C)'); ax.set_ylabel('density (kg/m3)')
ax.set_title('B2: argon must reach 131C to become buoyant vs 20C air'); ax.legend(); ax.grid(alpha=.3)
plt.tight_layout(); plt.savefig('fig_B2_argon.png',dpi=110); plt.close()
print('figures written: fig_B1_blockage.png, fig_B3_weather.png, fig_B2_argon.png')

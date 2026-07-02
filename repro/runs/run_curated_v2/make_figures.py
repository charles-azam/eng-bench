"""Generate figures + a results summary for the calculation note."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json
from rccs_model import solve_flow, solve_thermal, K2C
from transient_and_sensitivity import run_transient, P_section, ambient_sweep, wind_sweep, ETA_SECTION

# --- Transient figure ---
ts_w,Tw,Pw,Qw,pkw,ptw = run_transient(10.0,"winter")
ts_s,Tss,Ps,Qs,pks,pts = run_transient(25.0,"summer")
fig,ax = plt.subplots(1,2,figsize=(11,4))
ax[0].plot(ts_w,Pw,'r-',label='section power (kWt)')
ax[0].plot(ts_w,Qw,'b--',label='heat removed (kW)')
ax[0].set_xlabel('time (h)'); ax[0].set_ylabel('power (kW)'); ax[0].legend(); ax[0].grid(alpha=.3)
ax[0].set_title('Accident decay-heat load vs removal')
ax[1].plot(ts_w,Tw,'b-',label=f'winter 10C (peak {pkw:.0f}C)')
ax[1].plot(ts_s,Tss,'r-',label=f'summer 25C (peak {pks:.0f}C)')
ax[1].axhline(427,color='k',ls=':',label='RPV limit ~427C')
ax[1].set_xlabel('time (h)'); ax[1].set_ylabel('heated-wall (vessel) T (C)')
ax[1].legend(); ax[1].grid(alpha=.3); ax[1].set_title('Vessel temperature: levels off, no runaway')
plt.tight_layout(); plt.savefig('fig_transient.png',dpi=110)
print("saved fig_transient.png")

# --- Ambient sweep figure ---
Tas = np.arange(-18,33,2.0)
md=[]; dT=[]; vess=[]
for Ta in Tas:
    fl=solve_flow(56e3,Ta+273.15); th=solve_thermal(56e3,fl)
    md.append(fl['mdot']); dT.append(fl['dT']); vess.append(K2C(th['T_plate']))
fig,ax=plt.subplots(1,3,figsize=(13,3.6))
ax[0].plot(Tas,md,'b-o',ms=3); ax[0].set_xlabel('outdoor T (C)'); ax[0].set_ylabel('mass flow (kg/s)'); ax[0].grid(alpha=.3)
ax[1].plot(Tas,dT,'g-o',ms=3); ax[1].set_xlabel('outdoor T (C)'); ax[1].set_ylabel('riser air dT (C)'); ax[1].grid(alpha=.3)
ax[2].plot(Tas,vess,'r-o',ms=3); ax[2].set_xlabel('outdoor T (C)'); ax[2].set_ylabel('vessel T (C)'); ax[2].grid(alpha=.3)
fig.suptitle('Sensitivity to outdoor air temperature (Q=56 kWt)')
plt.tight_layout(); plt.savefig('fig_ambient.png',dpi=110)
print("saved fig_ambient.png")

# --- Wind sweep figure ---
from rccs_model import rho_air
V=np.arange(0,11,1.0); Cp=0.5; rho_a=rho_air(273.15)
ma=[]; mo=[]
for v in V:
    dP=Cp*0.5*rho_a*v**2
    ma.append(solve_flow(56e3,273.15,extra_stack_dP=+dP)['mdot'])
    try: mo.append(solve_flow(56e3,273.15,extra_stack_dP=-dP)['mdot'])
    except: mo.append(np.nan)
plt.figure(figsize=(6,4))
plt.plot(V,ma,'b-o',ms=3,label='wind assists draft')
plt.plot(V,mo,'r-o',ms=3,label='wind opposes draft')
plt.axhline(0.576,color='k',ls=':',label='no wind')
plt.xlabel('wind speed (m/s)'); plt.ylabel('mass flow (kg/s)'); plt.legend(); plt.grid(alpha=.3)
plt.title('Wind sensitivity (|Cp|=0.5, T_amb=0C)')
plt.tight_layout(); plt.savefig('fig_wind.png',dpi=110)
print("saved fig_wind.png")

# --- Results summary JSON ---
def case(Q,Ta):
    fl=solve_flow(Q,Ta+273.15); th=solve_thermal(Q,fl)
    return dict(Q_kW=Q/1e3,T_amb_C=Ta,mdot=round(fl['mdot'],3),dT=round(fl['dT'],1),
                T_out_C=round(K2C(fl['T_out']),1),riser_wall_C=round(K2C(th['T_rw']),1),
                vessel_C=round(K2C(th['T_plate']),1),rad_pct=round(100*th['frac_rad'],0),
                q_rad_kW=round(th['q_rad']/1e3,1),q_conv_kW=round(th['q_conv']/1e3,1))
summary=dict(
  baseline_peak_winter=case(56e3,0.0),
  normal_winter=case(26.16e3,0.0),
  baseline_peak_summer=case(56e3,25.0),
  accident_peak_vessel_C=dict(winter=round(pkw,1),summer=round(pks,1),time_h=round(ptw,1)),
  eta_section=round(ETA_SECTION,3))
json.dump(summary,open('results_summary.json','w'),indent=2)
print("saved results_summary.json"); print(json.dumps(summary,indent=2))

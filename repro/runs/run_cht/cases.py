"""Driver: run all operating cases, transient, weather sweep. Writes results.json
and figures."""
import json, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d
import model as m
import geom as g, props as pr

R={}

# ---------------------------------------------------------------------------
# CASE 1 baseline (Q_air = 56 kW net, design peak duty)
# ---------------------------------------------------------------------------
c1=m.full_case(56000.0, Tin_C=20, Tamb_C=2, label="Case1 baseline")
R['case1']=c1
# sensitivity: if parasitic loss lower -> more air-side heat
c1b=m.full_case(70000.0, Tin_C=20, Tamb_C=2, label="Case1 hi-Q (70kW to air)")
c1c=m.full_case(26160.0, Tin_C=20, Tamb_C=2, label="Normal-op duty 26 kW")
R['case1_hiQ']=c1b; R['normal_duty']=c1c

# ---------------------------------------------------------------------------
# CASE 2 accident transient : decay-heat polynomial (electric W), t minutes
# ---------------------------------------------------------------------------
# The digitized 10th-order polynomial is missing its C10 term and diverges for large t
# (gives ~83 kW at 85 h, not the documented 56 kW peak) -> unreliable at the tail.
# Per input 04, use the sanctioned normalized SHAPE instead: air-side decay heat rises
# 26 -> 56 kW, peaks at t = 84.85 h, then decays. Gamma-shaped pulse hits both anchors:
Q_MIN=26160.0; Q_PK=56070.0; TPK_H=84.85
def Q_elec(t_min):
    th=t_min/60.0
    gpk=(th/TPK_H)*np.exp(1.0-th/TPK_H)   # 0 at t=0, =1 at t=TPK_H, decays after
    return Q_MIN+(Q_PK-Q_MIN)*max(gpk,0.0)
tpk_min=TPK_H*60
print("Q_shape peak t=84.85h:", Q_elec(tpk_min), "W ; t=0:", Q_elec(0))

# Build steady Qrem(Tp) map for quasi-steady transient
Qs=np.linspace(15000,60000,25)
Tp_of_Q=[];
for Q in Qs:
    r=m.full_case(Q,Tin_C=20,Tamb_C=2)
    Tp_of_Q.append(r['Tp_C'])
Tp_of_Q=np.array(Tp_of_Q)
Q_of_Tp=interp1d(Tp_of_Q,Qs,fill_value="extrapolate")   # Qrem given plate temp

# lumped-capacitance transient of the plate/structure
Ctot=3.0e6   # J/K total steel+heater+insulation heat capacity (estimate)
def rhs(t_s,Tp):
    tmin=t_s/60.0
    Qin=max(Q_elec(tmin),0.0)
    Qrem=float(Q_of_Tp(Tp[0]))
    return [(Qin-Qrem)/Ctot]
# integrate 0..170 h
t_end=170*3600
sol=solve_ivp(rhs,[0,t_end],[20.0],max_step=1800,dense_output=True,rtol=1e-6)
th=sol.t/3600; Tp_t=sol.y[0]
# quasi-steady reference (instantaneous steady plate for Q(t))
Qin_t=np.array([max(Q_elec(t/60),0) for t in sol.t])
Tp_ss=np.interp(Qin_t,Qs,Tp_of_Q)
ipk=np.argmax(Tp_t)
R['case2']=dict(t_peak_h=float(th[ipk]), Tp_peak_C=float(Tp_t[ipk]),
                Q_peak_W=float(Qin_t.max()),
                Tp_peak_steady_C=float(m.full_case(56000,Tin_C=20,Tamb_C=2)['Tp_C']),
                Ctot=Ctot, tau_h=Ctot/408/3600)
# also record riser+mdot at peak
rpk=m.full_case(float(Qin_t.max()),Tin_C=20,Tamb_C=2)
R['case2'].update(mdot_peak=rpk['mdot'], Tfront_peak_C=rpk['Tfront_C'],
                  Tout_peak_C=rpk['Tout_C'])

fig,ax=plt.subplots(1,2,figsize=(11,4))
ax[0].plot(th,Qin_t/1000,'r-'); ax[0].set_xlabel("time (h)"); ax[0].set_ylabel("air-side heat (kW)")
ax[0].set_title("Decay-heat curve (½-scale)"); ax[0].grid(alpha=.3)
ax[1].plot(th,Tp_t,'b-',label="plate (transient, C=3MJ/K)")
ax[1].plot(th,Tp_ss,'k--',label="plate (quasi-steady)")
ax[1].axhline(550,color='r',ls=':',label="safe limit ~550C")
ax[1].set_xlabel("time (h)"); ax[1].set_ylabel("plate temp (C)"); ax[1].legend(); ax[1].grid(alpha=.3)
ax[1].set_title("Accident transient: peak %.0f C at %.1f h"%(Tp_t[ipk],th[ipk]))
plt.tight_layout(); plt.savefig("figs/case2_transient.png",dpi=110)

# ---------------------------------------------------------------------------
# CASE 3 weather sensitivity : outdoor T -18..24 C, wind 0..11 m/s
# ---------------------------------------------------------------------------
Touts=np.linspace(-18,24,15)
mdas=[]; dTs=[]; Tps=[]
for To in Touts:
    r=m.full_case(56000.0,Tin_C=20,Tamb_C=To)   # inlet building air fixed 20C
    mdas.append(r['mdot']); dTs.append(r['dT']); Tps.append(r['Tp_C'])
R['weather_T']=dict(Tout=list(Touts),mdot=mdas,dT=dTs,Tp=Tps)

winds=np.linspace(0,11,12)
mdaw=[]; Tpw=[]
for w in winds:
    r=m.full_case(56000.0,Tin_C=20,Tamb_C=2,wind=w,K_wind=1.0) # adverse gust at outlet
    mdaw.append(r['mdot']); Tpw.append(r['Tp_C'])
R['weather_wind']=dict(wind=list(winds),mdot=mdaw,Tp=Tpw)

fig,ax=plt.subplots(1,2,figsize=(11,4))
ax[0].plot(Touts,np.array(mdas)*60,'o-'); ax[0].set_xlabel("outdoor T (C)")
ax[0].set_ylabel("mass flow (kg/min)"); ax[0].grid(alpha=.3)
ax2=ax[0].twinx(); ax2.plot(Touts,Tps,'r^--'); ax2.set_ylabel("plate T (C)",color='r')
ax[0].set_title("Sensitivity to outdoor air temperature")
ax[1].plot(winds,np.array(mdaw)*60,'s-'); ax[1].set_xlabel("adverse wind (m/s)")
ax[1].set_ylabel("mass flow (kg/min)"); ax[1].grid(alpha=.3)
ax[1].set_title("Sensitivity to adverse chimney-exit wind")
plt.tight_layout(); plt.savefig("figs/case3_weather.png",dpi=110)

# ---------------------------------------------------------------------------
def clean(o):
    if isinstance(o,dict): return {k:clean(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)): return [clean(x) for x in o]
    if isinstance(o,(np.floating,np.integer)): return float(o)
    return o
json.dump(clean(R),open("results.json","w"),indent=2)
print("\n=== SUMMARY ===")
print("Case1: mdot=%.3f kg/s (%.1f kg/min) dT=%.1f Tp=%.0f Tfront=%.0f radfrac=%.1f%%"%(
    c1['mdot'],c1['mdot_kgmin'],c1['dT'],c1['Tp_C'],c1['Tfront_C'],c1['frac_rad']*100))
print("Case2 peak: t=%.1fh Q=%.1fkW Tp=%.0fC (steady=%.0f) tau=%.1fh -> %s"%(
    R['case2']['t_peak_h'],R['case2']['Q_peak_W']/1e3,R['case2']['Tp_peak_C'],
    R['case2']['Tp_peak_steady_C'],R['case2']['tau_h'],
    "LEVELS OFF" if R['case2']['Tp_peak_C']<550 else "RUNAWAY"))
print("Weather T: mdot %.1f->%.1f kg/min over Tout -18..24C"%(mdas[0]*60,mdas[-1]*60))
print("Wind: mdot %.1f->%.1f kg/min over 0..11 m/s adverse"%(mdaw[0]*60,mdaw[-1]*60))

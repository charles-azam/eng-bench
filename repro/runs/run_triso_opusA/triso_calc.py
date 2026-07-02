#!/usr/bin/env python3
"""
TRISO accident-heating failure & release predictions (offline).
All correlations from inputs/03_material_properties.md (TECDOC-1674 annex).
Schedule-integrated model.
"""
import numpy as np
from math import gamma

R = 8.314; NA = 6.02214e23
def K(Tc): return Tc + 273.15

# ---------- geometry ----------
def geom(kd, buf, ipyc, sic, opyc, rho_buf):
    a=kd/2*1e-6; r_i=(kd/2+buf+ipyc)*1e-6; r_o=r_i+sic*1e-6
    rb_o=(kd/2+buf)*1e-6
    V=4/3*np.pi*(rb_o**3-a**3); poros=1-rho_buf/2.10
    return dict(a=a,r_i=r_i,r_o=r_o,r_m=0.5*(r_i+r_o),t=sic*1e-6,V_void=poros*V,poros=poros)
G_K3=geom(497,94,41,36,40,1.00); G_P4=G_K3; G_K6=geom(508,102,39,36,38,1.02)

# ---------- inventory ----------
M_U=238.0; Y_gas=0.31; Y_CO=0.15
def nHM(hm,npart): return (hm/npart)/M_U*NA

# ---------- diffusion (reduced D'=D/r^2, s^-1) ----------
def Dp_gas(Tc):       return 5.0e-3*np.exp(-155400/(R*K(Tc)))
def Dp_Cs_kernel(Tc): return 0.90 *np.exp(-209000/(R*K(Tc)))
def D_Cs_SiC(Tc):     return 1.011e-16*np.exp(-(125000/R)*(1/K(Tc)-1/K(1600)))  # anchored to annex ref

# ---------- equivalent-sphere release from cumulative tau=integral(D' dt) ----------
def F_release(tau):
    if tau<=0: return 0.0
    if tau<=0.15: return max(0.0,6*np.sqrt(tau/np.pi)-3*tau)
    return 1-(6/np.pi**2)*np.exp(-np.pi**2*tau)

# ---------- Weibull ----------
SIC_MEAN=873.0; SIC_M=8.02; SIC_SCALE=SIC_MEAN/gamma(1+1/SIC_M)
def Pf_sic(s):
    return 0.0 if s<=0 else 1-np.exp(-(s/SIC_SCALE)**SIC_M)

# ---------- residual SiC compression from irradiation, thermally annealed ----------
def sigma_res(flu018,Tc):
    base=min(60.0*(flu018/5.0)**2,300.0)
    anneal=np.exp(-(Tc-1500)/250.0) if Tc>1500 else 1.0
    return base*max(anneal,0.15)

# ---------- schedules: list of (T_C, duration_h) for holds+ramps ----------
# ramps represented at mean temperature of endpoints
def sched(rows):  # rows: (T,dur)
    return rows
SCH={
 "A1":[(300,0.5),(675,1.5),(1050,5.5),(1150,0.5),(1250,16.5),(1400,6.5),
       (925,1),(950,9),(1600,500)],
 "A2":[(300,0.5),(675,1.5),(1050,5.5),(1150,0.5),(1250,13.5),(1525,12),(1800,25.5),
       (1050,1),(675,1.5),(1050,19.5),(1150,0.5),(1250,19),(1525,12),(1800,74.5)],
 "B" :[(300,7),(675,2),(1050,13.5),(1325,11),(1600,99),(810,17),
       (860,5.5),(1700,100),(860,17),(910,2),(1800,100),(910,17),(1050,7),(1050,1),(1800,300)],
 "C1":[(300,0.5),(675,1.5),(1050,5.5),(1150,0.5),(1250,13.5),(1425,7.5),(1600,304)],
 "C2":[(300,0.5),(675,1.5),(1050,5.5),(1150,0.5),(1250,13.5),(1425,7.5),(1600,304)],
}

cases=[
 dict(name="A1",G=G_K3,npart=16400,hm=10.22,   fima=0.077,flu01=3.9,thr=6.1e-5),
 dict(name="A2",G=G_K3,npart=16400,hm=10.22,   fima=0.106,flu01=6.0,thr=6.1e-5),
 dict(name="B", G=G_K6,npart=14580,hm=9.4346,  fima=0.109,flu01=4.8,thr=6.9e-5),
 dict(name="C1",G=G_P4,npart=1631, hm=1.018,   fima=0.139,flu01=7.5,thr=6.1e-4),
 dict(name="C2",G=G_P4,npart=1631, hm=1.018,   fima=0.111,flu01=5.5,thr=6.1e-4),
]

print(f"SiC scale strength = {SIC_SCALE:.0f} MPa (mean {SIC_MEAN}, m={SIC_M})\n"+"="*90)
summary=[]
for c in cases:
    G=c['G']; flu018=c['flu01']/1.10; nhm=nHM(c['hm'],c['npart']); Nf=c['fima']*nhm
    tau_cs=0.0; tau_gas=0.0; tau_csk=0.0
    maxPf=0.0; onset=None; peakP=0; peakS=0
    for (T,dur) in SCH[c['name']]:
        dt=dur*3600
        tau_gas+=Dp_gas(T)*dt
        tau_cs +=D_Cs_SiC(T)/G['r_m']**2*dt
        tau_csk+=Dp_Cs_kernel(T)*dt
        # pressure using gas released so far, at this T
        F_g=F_release(tau_gas)
        n_void=(Y_gas*Nf*F_g+Y_CO*Nf)/NA
        P=n_void*R*K(T)/G['V_void']; sig_p=P*G['r_m']/(2*G['t'])/1e6
        sig_net=sig_p-sigma_res(flu018,T); pf=Pf_sic(sig_net)
        if pf>maxPf: maxPf=pf; peakP=P/1e6; peakS=sig_net
        if pf*c['npart']>=0.5 and onset is None: onset=(T,dur)
    nfail=maxPf*c['npart']
    F_cs_intact=F_release(tau_cs)
    F_gas_failed=F_release(tau_gas)
    F_cs_failed =F_release(tau_csk)
    ff=nfail/c['npart']
    Kr=ff*F_gas_failed
    Cs=ff*F_cs_failed+(1-ff)*F_cs_intact
    summary.append((c['name'],nfail,Kr,Cs,peakP,peakS,maxPf,F_cs_intact))
    print(f"\n--- {c['name']} ---  fissions/part={Nf:.3e}  void={G['V_void']:.2e} m^3")
    print(f"  peak SiC net tension  ~ {peakS:.0f} MPa  (P~{peakP:.0f} MPa)")
    print(f"  Weibull Pf/particle   = {maxPf:.2e}  -> E[N_fail]={nfail:.3f}/{c['npart']}")
    print(f"  onset (Pf*N>=0.5)     = {onset}")
    print(f"  tau_Cs,SiC={tau_cs:.3e}  Cs release via intact SiC = {F_cs_intact:.3f}")
    print(f"  tau_gas={tau_gas:.3f} (F={F_gas_failed:.3f})  tau_Cs,kernel={tau_csk:.2f} (F={F_cs_failed:.3f})")
    print(f"  ==> Kr-85  frac release = {Kr:.2e}   ({Kr/c['thr']*1 if False else nfail:.3f} equiv failed part.)")
    print(f"  ==> Cs-137 frac release = {Cs:.3f}")

print("\n"+"="*90+"\nRANKING by Cs-137 release (severity):")
for n,nf,kr,cs,pp,ps,pf,fi in sorted(summary,key=lambda x:-x[3]):
    print(f"  {n}: Cs={cs:.3f}  Kr={kr:.2e}  E[Nfail]={nf:.3f}")
print("\nRANKING by peak SiC failure probability:")
for n,nf,kr,cs,pp,ps,pf,fi in sorted(summary,key=lambda x:-x[6]):
    print(f"  {n}: Pf/part={pf:.2e} E[Nfail]={nf:.3f}  peakNetStress={ps:.0f} MPa")

"""
TRISO accident-heating failure & release model (fully offline).
Built only from inputs/01,02,03. Correlations cited in the calculation note.

Model summary
-------------
1. INTERNAL PRESSURE (pressure-vessel driver of SiC failure)
   - Fissions/particle from kernel U inventory * burnup(%FIMA).
   - Fission-gas atoms = Y_gas * fissions, released into buffer void on heating
     (release-to-void fraction from kernel diffusion, sec.4/6).
   - Ideal gas: P = n R T / V_void ; V_void from buffer porosity.
   - CO carried as an explicit sensitivity band (no CO correlation is given).

2. SiC STRESS
   - Pressure term with elastic load-sharing across IPyC/SiC/OPyC membranes.
   - Residual irradiation compression in SiC from PyC shrinkage + irradiation
     creep, integrated over fast fluence with correlations (e) [swelling] and
     the Table-9.14 scalar creep coefficient. Retained (protective) on heating.
   - Net SiC tangential stress = residual(neg) + pressure(pos).

3. FAILURE by Weibull (sigma0=873 MPa, m=8.02) with particle-to-particle
   geometry scatter (Monte-Carlo over layer thicknesses + kernel size), each
   sample contributing its analytic Weibull failure probability.

4. RELEASE
   - Kr-85: only from failed particles; a failed kernel releases ~F_gas of its
     gas (sec.6 equivalent sphere, kernel gas D sec.4). Kr fract release =
     (N_fail/N_tot)*F_gas.
   - Cs-137: failed particles release ~F_Cs,kernel(~1); intact particles leak
     through SiC (sec.5 D_Cs,SiC, equivalent-sphere at particle radius).
"""
import numpy as np

R = 8.314
NA = 6.022e23

# ---------------------------------------------------------------- geometry
# (kernel dia, buffer, IPyC, SiC, OPyC) mean & sd, micron ; densities Mg/m3
GEO = {
 'K3': dict(kd=(497,14.1), buf=(94,10.3), ipyc=(41,4.0), sic=(36,1.7), opyc=(40,2.2),
            rho_k=10.81, rho_buf=1.00),
 'K6': dict(kd=(508,10.0), buf=(102,11.5), ipyc=(39,3.9), sic=(36,3.4), opyc=(38,3.5),
            rho_k=10.72, rho_buf=1.02),
 'P4': dict(kd=(497,14.1), buf=(94,10.3), ipyc=(41,4.0), sic=(36,1.7), opyc=(40,2.2),
            rho_k=10.81, rho_buf=1.00),
}

# elastic (Table 9.6)
E_P, nu_P = 3.96e4, 0.33
E_S, nu_S = 3.70e5, 0.13
Estar_P = E_P/(1-nu_P)
Estar_S = E_S/(1-nu_S)

# strengths (Table 9.14)
SIC_S0, SIC_M = 873.0, 8.02

# creep coeff (Table 9.14 scalar) per MPa per 1e25 n/m2 (E>0.18)
KCREEP = 4.93e-4
NU_CREEP = 0.4

# PyC swelling correlation (e), tangential, rate per 1e25 n/m2 (E>0.18)
def sdot_tang(x):
    if x <= 6.08:
        return -3.24737e-2 + 9.07826e-3*x - 2.10029e-3*x**2 + 1.30457e-4*x**3
    return -0.0249

# ---- residual SiC tangential stress from irradiation (creep-relaxed) -------
def residual_sic_stress(fluence_018, t_ipyc, t_sic, t_opyc):
    """Integrate 2-membrane (lumped PyC vs SiC) creep model over fluence.
    Returns EOL SiC tangential stress (MPa, negative=compression)."""
    a = (1-nu_S)/E_S
    b = (1-nu_P)/E_P
    t_p = t_ipyc + t_opyc
    r_ts_tp = t_sic/t_p
    fcreep = (1-NU_CREEP)          # equibiaxial creep factor
    sig = 0.0
    n = 400
    dx = fluence_018/n
    for i in range(n):
        x = (i+0.5)*dx
        sd = sdot_tang(x)
        dsig = (sd - KCREEP*fcreep*r_ts_tp*sig)/(a + b*r_ts_tp)
        sig += dsig*dx
    return sig

# --------------- kernel fission inventory ----------------------------------
M_UO2 = 269.8  # g/mol (LEU)
def U_atoms(kd_um, rho_k):
    r = kd_um*1e-6/2
    V = 4/3*np.pi*r**3          # m3
    mass = rho_k*1e3*V          # kg  (Mg/m3 = 1e3 kg/m3)
    mass_g = mass*1e3
    mol = mass_g/M_UO2
    return mol*NA               # U atoms (=UO2 molecules)

Y_GAS = 0.30   # stable+long-lived Xe+Kr atoms per fission

# --------------- void volume -----------------------------------------------
RHO_PYC_TH = 2.10  # theoretical dense pyrocarbon (for buffer porosity)
def void_volume(kd, buf, rho_buf):
    r_k = kd*1e-6/2
    r_bo = r_k + buf*1e-6
    V_buf = 4/3*np.pi*(r_bo**3 - r_k**3)
    poros = 1 - rho_buf/RHO_PYC_TH
    return V_buf*poros          # m3

# --------------- diffusion release helpers ---------------------------------
def F_equiv_sphere(Dp, t):
    """cumulative fractional release, reduced-sphere (Dp = D/r^2, 1/s)."""
    Dt = Dp*t
    if Dt <= 0.15:
        return max(0.0, 6*np.sqrt(Dt/np.pi) - 3*Dt)
    return 1 - (6/np.pi**2)*np.exp(-np.pi**2*Dt)

def D_gas_kernel(T):     # reduced, sec.4 stable/long-lived gas
    return 5e-3*np.exp(-155400/(R*T))
def D_Cs_kernel(T):
    return 0.90*np.exp(-209000/(R*T))
# Cs-in-SiC: anchor to annex-stated 1600C value, scale with dominant 125 kJ term
D_CS_SIC_1600 = 1.011e-16
def D_Cs_SiC(T):
    return D_CS_SIC_1600*np.exp(-(125000/R)*(1/T - 1/1873.15))

# ---------------- pressure & stress at a hold ------------------------------
def pressure(n_atoms_gas, V_void, T, co_factor=1.0):
    n_mol = n_atoms_gas/NA*co_factor
    P = n_mol*R*T/V_void        # Pa
    return P/1e6                # MPa

def sic_press_stress(P, r_mid, t_ipyc, t_sic, t_opyc):
    sumEt = Estar_P*(t_ipyc+t_opyc) + Estar_S*t_sic
    return P*r_mid*Estar_S/(2*sumEt)

# ============================ CASES ========================================
CASES = {
 'A1': dict(geo='K3', N=16400, bu=7.7,  flu01=3.9, Theat=1600, thold=500,  onset='1600C hold'),
 'A2': dict(geo='K3', N=16400, bu=10.6, flu01=6.0, Theat=1800, thold=100,  onset='1800C exposure'),
 'B' : dict(geo='K6', N=14580, bu=10.9, flu01=4.8, Theat=1800, thold=400,  onset='1800C stages',
            stages=[(1600,100),(1700,100),(1800,100),(1800,300)]),
 'C1': dict(geo='P4', N=1631,  bu=13.9, flu01=7.5, Theat=1600, thold=304,  onset='1600C hold'),
 'C2': dict(geo='P4', N=1631,  bu=11.1, flu01=5.5, Theat=1600, thold=304,  onset='1600C hold'),
}

rng = np.random.default_rng(20260702)
NSAMP = 200000

def run_case(c, co_factor=1.0, retain_frac=1.0, verbose=True):
    g = GEO[c['geo']]
    flu018 = c['flu01']/1.10
    T = c['Theat']+273.15
    thold_s = c['thold']*3600

    # ---- mean-geometry deterministic values
    kd,buf,ip,si,op = g['kd'][0],g['buf'][0],g['ipyc'][0],g['sic'][0],g['opyc'][0]
    Uat = U_atoms(kd, g['rho_k'])
    Nf = c['bu']/100*Uat
    Vv = void_volume(kd,buf,g['rho_buf'])
    # gas released to void during heating (kernel gas diffusion)
    Fg = F_equiv_sphere(D_gas_kernel(T), thold_s)
    n_gas = Y_GAS*Nf*Fg
    P = pressure(n_gas, Vv, T, co_factor)
    r_mid = (kd/2+buf+ip+si/2)   # micron, SiC mid radius
    sp = sic_press_stress(P, r_mid, ip, si, op)
    sr = residual_sic_stress(flu018, ip, si, op)*retain_frac
    net = sp+sr

    # ---- Monte-Carlo failure count
    kds = rng.normal(kd, g['kd'][1], NSAMP).clip(kd-3*g['kd'][1], None)
    bufs= rng.normal(buf, g['buf'][1], NSAMP).clip(20,None)
    ips = rng.normal(ip, g['ipyc'][1], NSAMP).clip(10,None)
    sis = rng.normal(si, g['sic'][1], NSAMP).clip(10,None)
    ops = rng.normal(op, g['opyc'][1], NSAMP).clip(10,None)
    Uat_s = U_atoms(kds, g['rho_k'])
    Nf_s  = c['bu']/100*Uat_s
    Vv_s  = void_volume(kds,bufs,g['rho_buf'])
    n_gas_s = Y_GAS*Nf_s*Fg
    P_s = pressure(n_gas_s, Vv_s, T, co_factor)
    r_mid_s = kds/2+bufs+ips+sis/2
    sumEt_s = Estar_P*(ips+ops)+Estar_S*sis
    sp_s = P_s*r_mid_s*Estar_S/(2*sumEt_s)
    # residual stress varies mainly through t_sic/t_pyc ratio
    sr_s = np.array([residual_sic_stress(flu018, ips[i], sis[i], ops[i])
                     for i in range(0,NSAMP,50)])   # coarse; interpolate
    # cheaper: residual scales ~ with t_pyc/t_sic ; use analytic steady form
    fcreep=(1-NU_CREEP)
    sd = sdot_tang(flu018)
    ss_ss = sd/(KCREEP*fcreep*(sis/(ips+ops)))    # steady-state approx (MPa,neg)
    # blend: use integrated mean-geo value scaled by steady-state ratio
    sr_ref = sr/retain_frac
    ss_ref = sd/(KCREEP*fcreep*(si/(ip+op)))
    sr_s_all = sr_ref*(ss_ss/ss_ref)*retain_frac
    net_s = sp_s + sr_s_all
    net_pos = np.clip(net_s,0,None)
    pf = 1-np.exp(-(net_pos/SIC_S0)**SIC_M)
    Nfail = c['N']*pf.mean()

    # ---- staged (case B): accumulate over stages
    Nfail_stage = None
    if 'stages' in c:
        cumulative_pf = np.zeros(NSAMP)
        Nfail_stage=[]
        for (Ts,ts) in c['stages']:
            Tk=Ts+273.15; ts_s=ts*3600
            Fg_st = F_equiv_sphere(D_gas_kernel(Tk), ts_s)
            # gas is cumulative; approximate full release reached => use max
            n_st = Y_GAS*Nf_s*max(Fg_st,Fg_prev if False else Fg_st)
            P_st = pressure(n_st, Vv_s, Tk, co_factor)
            sp_st = P_st*r_mid_s*Estar_S/(2*sumEt_s)
            net_st = np.clip(sp_st+sr_s_all,0,None)
            pf_st = 1-np.exp(-(net_st/SIC_S0)**SIC_M)
            new_pf = np.maximum(cumulative_pf, pf_st)
            Nfail_stage.append((Ts,ts, c['N']*(new_pf.mean())))
            cumulative_pf=new_pf
        Nfail = c['N']*cumulative_pf.mean()

    # ---- releases
    Fg_release = F_equiv_sphere(D_gas_kernel(T), thold_s)          # failed kernel Kr
    Fcs_kernel = F_equiv_sphere(D_Cs_kernel(T), thold_s)
    # intact Cs leak through SiC, equiv sphere at particle (SiC-outer) radius
    r_part = (kd/2+buf+ip+si)*1e-6
    Dp_cs_sic = D_Cs_SiC(T)/r_part**2
    Fcs_intact = F_equiv_sphere(Dp_cs_sic, thold_s)
    ff = Nfail/c['N']
    Kr_rel = ff*Fg_release
    Cs_rel = ff*Fcs_kernel + (1-ff)*Fcs_intact

    if verbose:
        print(f"\n==== {c_name} ====")
        print(f" fluence(E>0.18)={flu018:.2f}  T_hold={c['Theat']}C  t={c['thold']}h")
        print(f" U atoms/kernel={Uat:.3e}  fissions/particle={Nf:.3e}")
        print(f" void volume={Vv:.3e} m3   F_gas(to void)={Fg:.3f}")
        print(f" gas atoms/particle={n_gas:.3e}  P(gas,co={co_factor})={P:.1f} MPa")
        print(f" sigma_press,SiC={sp:.1f}  sigma_resid={sr:.1f}  NET={net:.1f} MPa")
        print(f" mean MC net stress={net_s.mean():.1f} MPa  meanPf={pf.mean():.2e}")
        print(f" ==> N_fail (expected) = {Nfail:.3f}  of {c['N']}   (frac {ff:.2e})")
        if Nfail_stage:
            for (Ts,ts,nf) in Nfail_stage:
                print(f"     stage {Ts}C/{ts}h -> cumulative N_fail={nf:.3f}")
        print(f" Kr-85 release fraction = {Kr_rel:.2e}")
        print(f" Cs-137: F_intact(SiC)={Fcs_intact:.2e}  F_kernel={Fcs_kernel:.3f}")
        print(f" Cs-137 release fraction = {Cs_rel:.2e}")
    return dict(name=c_name, flu018=flu018, P=P, sp=sp, sr=sr, net=net,
                Nfail=Nfail, ff=ff, Kr=Kr_rel, Cs=Cs_rel,
                Fcs_intact=Fcs_intact, Fg=Fg, stages=Nfail_stage)

results={}
for c_name,c in CASES.items():
    results[c_name]=run_case(c, co_factor=1.0)

print("\n\n########## STRESS-TAIL & RELAXATION DIAGNOSTICS ##########")
def tail(c, co_factor, retain_frac):
    g=GEO[c['geo']]; flu018=c['flu01']/1.10; T=c['Theat']+273.15; thold_s=c['thold']*3600
    kd,buf,ip,si,op=g['kd'][0],g['buf'][0],g['ipyc'][0],g['sic'][0],g['opyc'][0]
    Fg=F_equiv_sphere(D_gas_kernel(T), thold_s)
    kds=rng.normal(kd,g['kd'][1],NSAMP).clip(kd-3*g['kd'][1],None)
    bufs=rng.normal(buf,g['buf'][1],NSAMP).clip(20,None)
    ips=rng.normal(ip,g['ipyc'][1],NSAMP).clip(10,None)
    sis=rng.normal(si,g['sic'][1],NSAMP).clip(10,None)
    ops=rng.normal(op,g['opyc'][1],NSAMP).clip(10,None)
    Nf_s=c['bu']/100*U_atoms(kds,g['rho_k']); Vv_s=void_volume(kds,bufs,g['rho_buf'])
    P_s=pressure(Y_GAS*Nf_s*Fg,Vv_s,T,co_factor)
    r_mid_s=kds/2+bufs+ips+sis/2; sumEt_s=Estar_P*(ips+ops)+Estar_S*sis
    sp_s=P_s*r_mid_s*Estar_S/(2*sumEt_s)
    fcreep=(1-NU_CREEP); sd=sdot_tang(flu018)
    ss_ss=sd/(KCREEP*fcreep*(sis/(ips+ops)))
    sr_ref=residual_sic_stress(flu018,ip,si,op); ss_ref=sd/(KCREEP*fcreep*(si/(ip+op)))
    sr_s=sr_ref*(ss_ss/ss_ref)*retain_frac
    net=sp_s+sr_s
    pf=1-np.exp(-(np.clip(net,0,None)/SIC_S0)**SIC_M)
    return net, c['N']*pf.mean()

for c_name,c in CASES.items():
    net,_=tail(c,1.0,1.0)
    print(f"{c_name}: net stress  p50={np.percentile(net,50):.0f}  p99.9={np.percentile(net,99.9):.0f}"
          f"  max={net.max():.0f} MPa   frac(net>0)={(net>0).mean():.2e}")

print("\n########## FAILURE vs protective-compression RETENTION (co=1.3) ##########")
for rf in (1.0,0.5,0.25,0.0):
    row=[]
    for c_name,c in CASES.items():
        _,nf=tail(c,1.3,rf); row.append(f"{c_name}={nf:.2g}")
    print(f" retain={rf:>4}: "+"  ".join(row))

print("\n########## Cs release characteristic-length sensitivity ##########")
for c_name,c in CASES.items():
    g=GEO[c['geo']]; T=c['Theat']+273.15; thold_s=c['thold']*3600
    kd,buf,ip,si,op=g['kd'][0],g['buf'][0],g['ipyc'][0],g['sic'][0],g['opyc'][0]
    r_part=(kd/2+buf+ip+si)*1e-6; r_sicmid=(kd/2+buf+ip+si/2)*1e-6; r_kern=(kd/2)*1e-6
    D=D_Cs_SiC(T)
    f_part=F_equiv_sphere(D/r_part**2,thold_s)
    f_kern=F_equiv_sphere(D/r_kern**2,thold_s)
    f_shell=F_equiv_sphere(D/(si*1e-6)**2,thold_s)  # SiC-thickness length (upper bound)
    print(f"{c_name} T={c['Theat']} t={c['thold']}h  Fcs[r_part]={f_part:.2e}"
          f"  Fcs[r_kernel]={f_kern:.2e}  Fcs[t_SiC]={f_shell:.2e}")

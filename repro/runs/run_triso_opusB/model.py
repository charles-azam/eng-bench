"""
TRISO accident-heating failure & release model (offline).
All physics from inputs/03_material_properties.md + standard fission physics.
Cases from inputs/02_cases.md.

Model chain per case:
  1. Per-kernel fission inventory  -> noble-gas moles (+ optional CO).
  2. Free (buffer void) volume.
  3. Internal pressure at peak T (ideal gas).
  4. SiC tangential membrane stress (thin spherical shell, SiC carries load).
  5. Weibull failure probability -> expected # failed particles.
  6. Kr-85 release  ~= failed fraction (bare kernel dumps ~all gas fast; §4/§6 check).
  7. Cs-137 release = failed*1 + intact * (Cs permeation through intact SiC shell, §5).
"""
import math

NA = 6.02214076e23
Rgas = 8.314

# ---------- geometry per batch (µm) ----------
# EUO2308 (K3, P4): kernel dia 497 ; buffer 94 ; IPyC 41 ; SiC 36 ; OPyC 40
# EUO2358 (K6):     kernel dia 508 ; buffer 102; IPyC 39 ; SiC 36 ; OPyC 38
def geom(kernel_d, buf, ipyc, sic, opyc, rho_kernel):
    rk = kernel_d/2.0            # kernel radius µm
    r_buf = rk + buf             # outer buffer
    r_ipyc = r_buf + ipyc        # inner SiC
    r_sic_o = r_ipyc + sic       # outer SiC
    # volumes in m^3 (µm->m : 1e-6)
    m = 1e-6
    Vk = 4/3*math.pi*(rk*m)**3
    # buffer void: porosity from density (theoretical PyC density 2.10 Mg/m3)
    rho_theo = 2.10
    return dict(rk=rk*m, r_buf=r_buf*m, r_ipyc=r_ipyc*m, r_sic_o=r_sic_o*m,
                t_sic=sic*m, Vk=Vk, rho_kernel=rho_kernel, buf_um=buf, rk_um=rk,
                r_buf_um=r_buf)

def buffer_void(g, buf_um, rho_buf, rho_theo=2.10):
    m=1e-6
    Vbuf = 4/3*math.pi*((g['r_buf'])**3 - (g['rk'])**3)
    por = 1 - rho_buf/rho_theo
    return Vbuf*por

def U_atoms_per_kernel(g):
    # UO2 molar mass ~270 g/mol -> U atoms = mass_UO2/270 * NA
    Vk_cm3 = g['Vk']*1e6   # m3 -> cm3
    mass = Vk_cm3 * g['rho_kernel']   # g (rho in g/cm3 = Mg/m3)
    return mass/270.03 * NA

# ---------- correlations ----------
def D_cs_sic(T_C):
    """Cs in SiC, anchored to 1.01e-16 m2/s at 1600C, scaled with Q=125 kJ/mol
       (dominant term of Eq 10.9)."""
    D1600 = 1.01e-16
    Q=125000.0
    T=T_C+273.15; T0=1600+273.15
    return D1600*math.exp(-Q/Rgas*(1/T-1/T0))

def D_kernel(D0p, Q, T_C):
    T=T_C+273.15
    return D0p*math.exp(-Q/(Rgas*T))   # reduced (s^-1)

def F_equiv_sphere(Dp_t):
    x=Dp_t
    if x<=0: return 0.0
    if x<=0.15:
        return 6*math.sqrt(x/math.pi)-3*x
    F=1-(6/math.pi**2)*math.exp(-math.pi**2*x)
    return min(F,1.0)

def weibull_pf(sigma, sigma_mean, m):
    # sigma0 = characteristic; mean = sigma0*Gamma(1+1/m)
    g=math.gamma(1+1/m)
    s0=sigma_mean/g
    return 1-math.exp(-(sigma/s0)**m), s0

# ---------- Cs permeation through intact SiC shell (reservoir model) ----------
# kernel = well-mixed reservoir (fast kernel diffusion at accident T), SiC = resistance.
# dN/dt = -4 pi D_s C /(1/r1 - 1/r2); N=C*Vk -> F=1-exp(-t/tau)
# tau = Vk*(1/r1-1/r2)/(4 pi D_s)
def tau_cs_sic(g, T_C):
    Ds=D_cs_sic(T_C)
    r1=g['r_ipyc']; r2=g['r_sic_o']
    return g['Vk']*(1/r1-1/r2)/(4*math.pi*Ds)

# ================= build cases =================
gK3 = geom(497,94,41,36,40,10.81)
gK6 = geom(508,102,39,36,38,10.72)
gP4 = geom(497,94,41,36,40,10.81)
for g,rhob in ((gK3,1.00),(gK6,1.02),(gP4,1.00)):
    g['Vfree']=buffer_void(g,g['buf_um'],rhob)
    g['NU']=U_atoms_per_kernel(g)

Ygas=0.31   # Xe+Kr atoms per fission (standard U-235/U-238 thermal cumulative noble-gas yield)

# Peak-condition list: (name, g, Nparticles, BU_fima, Tpeak_C, t_peak_h, note)
cases=[
 ("A1", gK3, 16400, 0.077, 1600, 500, "1600C/500h"),
 ("A2", gK3, 16400, 0.102, 1800, 100, "1800C/100h"),
 ("B",  gK6, 14580, 0.109, 1800, 400, "staged; 1800C total 400h (peak phase)"),
 ("C1", gP4, 1631,  0.139, 1600, 304, "1600C/304h"),
 ("C2", gP4, 1631,  0.111, 1600, 304, "1600C/304h"),
]

def run(co_factor):
    print(f"\n===== CO multiplier on gas moles = {co_factor} (n_total = Ygas*fis*(1+co)) =====")
    print(f"{'case':4} {'BU%':>5} {'fis/kern':>9} {'ngas(mol)':>10} {'Vfree(m3)':>10} "
          f"{'P(MPa)':>7} {'sig(MPa)':>8} {'Pf':>10} {'Nfail':>8}")
    res={}
    for name,g,Npart,bu,Tp,th,note in cases:
        fis=bu*g['NU']
        n=Ygas*fis*(1+co_factor)/NA
        T=Tp+273.15
        P=n*Rgas*T/g['Vfree']          # Pa
        r_mean=0.5*(g['r_ipyc']+g['r_sic_o'])
        sig=P*r_mean/(2*g['t_sic'])/1e6  # MPa
        Pf,s0=weibull_pf(sig,873,8.02)
        Nfail=Pf*Npart
        res[name]=dict(P=P/1e6,sig=sig,Pf=Pf,Nfail=Nfail,fis=fis,n=n,g=g,Npart=Npart,
                       Tp=Tp,th=th,bu=bu)
        print(f"{name:4} {bu*100:5.1f} {fis:9.3e} {n:10.3e} {g['Vfree']:10.3e} "
              f"{P/1e6:7.1f} {sig:8.1f} {Pf:10.3e} {Nfail:8.2f}")
    return res

# geometry / inventory dump
print("Geometry & inventory:")
for tag,g in (("K3",gK3),("K6",gK6),("P4",gP4)):
    print(f" {tag}: Vk={g['Vk']:.3e} m3  Vfree={g['Vfree']:.3e} m3  "
          f"U/kernel={g['NU']:.3e}  r_ipyc={g['r_ipyc']*1e6:.1f}um r_sico={g['r_sic_o']*1e6:.1f}um")

for co in (0.0, 0.5, 1.0):
    run(co)

# ---- Cs release (intact permeation) & bare-kernel checks, independent of CO ----
print("\n===== Cs / Kr release channels =====")
# staged schedule Cs for B computed with segments
def cs_intact_fraction_staged(g, segments):
    s=0.0
    for T_C,t_h in segments:
        tau=tau_cs_sic(g,T_C)
        s += t_h*3600/tau
    return 1-math.exp(-s)

cs_segments={
 "A1":[(1600,500)],
 "A2":[(1800,100)],
 "B":[(1600,100),(1700,100),(1800,400)],
 "C1":[(1600,304)],
 "C2":[(1600,304)],
}
print(f"{'case':4} {'tau1600h':>9} {'F_Cs_intact':>12}")
for name,g,Npart,bu,Tp,th,note in cases:
    tau1600=tau_cs_sic(g,1600)/3600
    Fcs=cs_intact_fraction_staged(g,cs_segments[name])
    print(f"{name:4} {tau1600:9.0f} {Fcs:12.4f}")

# bare-kernel release fractions (verify ~1 at accident T)
print("\nBare-kernel (failed) release fractions:")
for T_C,t_h in [(1600,500),(1800,100),(1600,304)]:
    # gas (stable): D0'=5e-3,Q=155.4 ; Cs: 0.90,209
    Dg=D_kernel(5e-3,155400,T_C); Dc=D_kernel(0.90,209000,T_C)
    t=t_h*3600
    print(f" T={T_C} t={t_h}h : F_gas={F_equiv_sphere(Dg*t):.3f}  F_Cs={F_equiv_sphere(Dc*t):.3f}")

# ---- SiC Cs breakthrough lag time L^2/(6D) ----
print("\nSiC Cs breakthrough lag  L^2/(6D)  [L=36um]:")
L=36e-6
for T in (1600,1700,1800):
    lag=L**2/(6*D_cs_sic(T))
    print(f"  {T}C : D={D_cs_sic(T):.3e}  lag={lag/3600:.0f} h")

# ---- consolidated final table (CO factor 1.0 best estimate) ----
print("\n===== CONSOLIDATED (CO factor 1.0) =====")
res=run(1.0)
print(f"\n{'case':4}{'Npart':>7}{'Pf':>11}{'Nfail':>7}{'F_Kr':>11}{'F_Cs_intact(reservoir)':>24}")
Fgas={'A1':0.99,'A2':0.93,'B':0.95,'C1':0.95,'C2':0.95}
for name,g,Npart,bu,Tp,th,note in cases:
    Fcs=cs_intact_fraction_staged(g,cs_segments[name])
    r=res[name]
    fk=(r['Nfail']/Npart)*Fgas[name]
    Fcs_tot=r['Pf']*1.0+(1-r['Pf'])*Fcs
    print(f"{name:4}{Npart:7d}{r['Pf']:11.2e}{r['Nfail']:7.2f}{fk:11.2e}{Fcs_tot:16.4f}")

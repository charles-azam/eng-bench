"""
HTTR LOFC coupled transient: point kinetics + fission-product decay heat +
2-node lumped graphite thermal model (active core + reflector) + VCS heat sink.

Reactivity feedback is driven by the OpenMC-computed k_inf(T) curve
(runs/main/keff.csv): the core reactivity change from the operating temperature,
Drho_core(T) = 1 - k_inf(Top)/k_inf(T)  (rods frozen -> constant multiplier).

Scenario: at t=0 the reactor is critical at 9 MWt (rods frozen); all He
circulators trip (no forced convection); VCS running. No scram.

Everything the transient needs that is neutronics is COMPUTED (k_inf(T), beta_eff);
thermal parameters are engineering estimates from public design data (see sources.md),
carried with a sensitivity analysis.
"""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d
import csv, sys

# ----------------------------------------------------------------------
# 1. Graphite specific heat Cp(T)  [J/kg/K]  (nuclear graphite, standard)
#    Butland-Maddison-like fit; ~710 @300K, ~1700 @1000K, ~2000 @2000K.
def cp_graphite(T):
    # T in K. Piecewise-smooth fit to standard nuclear-graphite Cp.
    # Butland & Maddison (1973) correlation for graphite:
    # Cp = 4184*(0.54212 - 2.42667e-6*T - 90.2725/T - 43449.3/T^2
    #            + 1.59309e7/T^3 - 1.43688e9/T^4)  [J/kg/K], T in K
    T = np.clip(T, 200.0, 3000.0)
    cp = 4184.0*(0.54212 - 2.42667e-6*T - 90.2725/T - 43449.3/T**2
                 + 1.59309e7/T**3 - 1.43688e9/T**4)
    return np.clip(cp, 400.0, 2200.0)

# ----------------------------------------------------------------------
# 2. Fission-product decay heat  P_d(t)/P0  (fraction of pre-trip fission power)
#    Todreas-Kazimi / Wigner-Way form for finite operating time t_op (s).
def decay_frac(t, t_op):
    # Wigner-Way form diverges as t->0; clamp to its ~1 s value (~6.3% for a
    # ~month-long history), which is the physical post-shutdown decay-heat fraction.
    t = np.maximum(t, 1.0)
    return 0.066*((t)**-0.2 - (t + t_op)**-0.2)

# ----------------------------------------------------------------------
# 3. Delayed-neutron 6-group data (U-235 thermal, Keepin) — group SHAPE.
#    Absolute beta_eff is scaled to the OpenMC-computed value.
BETA_I = np.array([0.000215,0.001424,0.001274,0.002568,0.000748,0.000273])
LAM_I  = np.array([0.0124,0.0305,0.111,0.301,1.14,3.01])
BETA0  = BETA_I.sum()   # ~0.0065

# ----------------------------------------------------------------------
def load_kT(csv_path='runs/main/keff.csv', bp=1):
    T, k, s = [], [], []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            if int(row['bp']) == bp and int(row['prompt_only']) == 0:
                T.append(float(row['T_K'])); k.append(float(row['keff']))
                s.append(float(row['keff_sigma']))
    idx = np.argsort(T)
    return np.array(T)[idx], np.array(k)[idx], np.array(s)[idx]

def make_drho(Tk, kk, Top):
    """Core reactivity change vs T relative to operating temp Top, from k_inf(T).
    Under a temperature-independent control-rod/leakage multiplier M (rods frozen)
    that makes the core critical at Top, k_eff(T)=k_inf(T)/k_inf(Top), so
    Drho_core(T)=(k_eff-1)/k_eff = 1 - k_inf(Top)/k_inf(T).  (Note: one power of k,
    not k^2 -- the constant multiplier cancels in the logarithmic derivative.)"""
    kfun = interp1d(Tk, kk, kind='quadratic', fill_value='extrapolate')
    kop = float(kfun(Top))
    def drho(T):
        kT = float(kfun(np.clip(T, Tk.min()-200, Tk.max()+400)))
        return 1.0 - kop/kT
    return drho, kfun

# ----------------------------------------------------------------------
def run(params, drho, beta_eff, verbose=False):
    p = params
    Top   = p['Top']          # operating core-avg graphite temp [K]
    P0    = p['P0']           # pre-trip fission power [W] (9 MW)
    Mc    = p['Mc']; Mr = p['Mr']   # core, reflector graphite masses [kg]
    Mv    = p.get('Mv', 100000.0)   # vessel steel mass [kg]
    Gcr   = p['Gcr']          # core<->reflector conductance [W/K]
    Grv   = p.get('Grv', 4000.0)    # reflector<->vessel conductance [W/K]
    Q0    = p['Q0']           # VCS removal at vessel op temp [W]
    Ts    = p['Ts']           # ultimate sink temp (VCS panel) [K]
    pexp  = p['pexp']         # exponent of VCS removal law
    t_op  = p['t_op']         # prior operating time [s] for decay heat
    Lam   = p['Lam']          # prompt neutron generation time [s]
    L0    = p.get('L0', 0.6e6)      # steady passive leak at operation [W]
    cp_v  = 500.0             # steel specific heat [J/kg/K]

    # steady-state operating temperatures of the chain (calibration)
    Tr_op = Top   - L0/Gcr
    Tv_op = Tr_op - L0/Grv

    beta_i = BETA_I*(beta_eff/BETA0)
    b_eff  = beta_i.sum()
    # intrinsic neutron source (spontaneous fission of U-238 + (a,n)); tiny.
    # Result is insensitive to its magnitude (only sharpens the power revival).
    S = p.get('S', 1e-6)*P0

    def Qvcs(Tv):
        return Q0*np.maximum((Tv-Ts)/(Tv_op-Ts), 0.0)**pexp

    # initial precursors for steady P0
    C0 = beta_i/(LAM_I*Lam)*P0
    y0 = np.concatenate([[P0], C0, [Top, Tr_op, Tv_op]])   # P, C1..6, Tc, Tr, Tv

    def rhs(t, y):
        P = max(y[0], 0.0)
        C = np.maximum(y[1:7], 0.0)
        Tc, Tr, Tv = y[7], y[8], y[9]
        rho = drho(Tc)
        dP = (rho - b_eff)/Lam*P + np.dot(LAM_I, C) + S
        dC = beta_i/Lam*P - LAM_I*C
        Pd = decay_frac(t, t_op)*P0
        # heat balances along core -> reflector -> vessel -> VCS
        qcr = Gcr*(Tc - Tr)
        qrv = Grv*(Tr - Tv)
        dTc = (P + Pd - qcr)/(Mc*cp_graphite(Tc))
        dTr = (qcr - qrv)/(Mr*cp_graphite(Tr))
        dTv = (qrv - Qvcs(Tv))/(Mv*cp_v)
        return np.concatenate([[dP], dC, [dTc, dTr, dTv]])

    t_end = p.get('t_end', 3.5*24*3600)
    teval = np.unique(np.concatenate([np.linspace(0,600,200),
                                      np.linspace(600, t_end, 4000)]))
    sol = solve_ivp(rhs, (0, t_end), y0, method='BDF', t_eval=teval,
                    rtol=1e-6, atol=[1e-2]+[1e-2]*6+[1e-3,1e-3,1e-3], max_step=60.0)
    return sol, b_eff

def summarize(sol, P0, Top, drho=None):
    t = sol.t; P = sol.y[0]; Tc = sol.y[7]; Tr = sol.y[8]; Tv = sol.y[9]
    # power minimum in first phase (first 30 min) -> initial collapse depth
    i30 = max(np.searchsorted(t, 1800), 3)
    Pmin_early = P[:i30].min()
    tmin = t[:i30][np.argmin(P[:i30])]
    # peak core temperature and its time
    ipk = np.argmax(Tc); Tc_peak = Tc[ipk]; tpeak = t[ipk]
    # recriticality: after the Tc peak, first time Tc cools back to Top
    # (feedback reactivity returns to zero, rods frozen). Linear-interpolate.
    trec = None
    for i in range(max(ipk,1), len(t)):
        if Tc[i] <= Top:
            t0,t1 = t[i-1], t[i]; y0,y1 = Tc[i-1]-Top, Tc[i]-Top
            trec = t0 + (t1-t0)*(y0/(y0-y1)) if y1 != y0 else t1
            break
    # stabilized fission power: mean over the last 10% of the trace
    n = max(int(0.1*len(t)), 5)
    P_stab = np.mean(P[-n:])
    return dict(Pmin_early=Pmin_early, tmin=tmin, trec=trec,
                Tc_peak=Tc_peak, tpeak=tpeak, P_stab=P_stab,
                Tc_end=Tc[-1], Tr_end=Tr[-1], P_end=P[-1],
                Tv_peak=Tv.max(), Tv_end=Tv[-1])

if __name__ == '__main__':
    bp = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    Top = float(sys.argv[2]) if len(sys.argv) > 2 else 820.0
    Tk, kk, sk = load_kT(bp=bp)
    print("k_inf(T):", list(zip(Tk, np.round(kk,5), np.round(sk,5))))
    drho, kfun = make_drho(Tk, kk, Top)
    # isothermal coefficient at a few T
    for T in [400,600,800,1000,1200]:
        a = (kfun(T+10)-kfun(T-10))/(20*kfun(T))*1e5
        print(f"  alpha_iso({T}K) = {a:8.2f} pcm/K")
    beta_eff = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0065
    params = dict(Top=Top, P0=9e6, Mc=14000.0, Mr=40000.0, Gcr=3000.0,
                  Q0=0.6e6, Ts=320.0, pexp=1.5, t_op=30*24*3600.0, Lam=1e-3,
                  t_end=3.5*24*3600)
    sol, beff = run(params, drho, beta_eff, verbose=True)
    s = summarize(sol, params['P0'], Top)
    print("beta_eff used:", beff)
    for k_,v in s.items():
        print(f"  {k_}: {v}")

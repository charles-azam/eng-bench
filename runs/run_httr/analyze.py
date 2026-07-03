"""
Final analysis: load OpenMC k_inf(T), compute isothermal temperature coefficient
alpha(T) with uncertainty, run nominal LOFC transient + sensitivity study, and
emit results (JSON) and a plot. Consumes runs/main/keff.csv (BP on).
"""
import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
import transient as TR

RNG = np.random.default_rng(12345)

def alpha_curve(Tk, kk, sk, Tq):
    """alpha(T)=dk/dT/k^2 [pcm/K] with 1-sigma via Monte Carlo over k points."""
    N = 4000
    a_samp = np.zeros((N, len(Tq)))
    dk_samp = np.zeros(N)  # slope 294->1200 overall
    for i in range(N):
        kp = kk + RNG.normal(0, 1, len(kk))*sk
        f = interp1d(Tk, kp, kind='quadratic', fill_value='extrapolate')
        for j, T in enumerate(Tq):
            # isothermal reactivity coefficient of the critical core = (1/k) dk/dT
            # (logarithmic derivative; rod/leakage multiplier cancels)
            a_samp[i, j] = (f(T+15)-f(T-15))/(30.0*f(T))*1e5
    return a_samp.mean(0), a_samp.std(0)

def main():
    Tk, kk, sk = TR.load_kT('runs/main/keff.csv', bp=1)
    print("k_inf(T)  [BP ON, main]:")
    for T,k,s in zip(Tk,kk,sk): print(f"  {T:6.1f} K : {k:.5f} +/- {s:.5f}")
    Tq = np.array([400,600,800,1000,1200.])
    am, asd = alpha_curve(Tk, kk, sk, Tq)
    print("isothermal temperature coefficient alpha(T)  [BP ON]:")
    for T,a,s in zip(Tq,am,asd): print(f"  alpha({T:.0f}K) = {a:7.2f} +/- {s:4.2f} pcm/K")

    # ---- second BP variant (burnable poison OFF) — brackets the coefficient ----
    Tk2, kk2, sk2 = TR.load_kT('runs/nobp/keff.csv', bp=0)
    print("\nk_inf(T)  [BP OFF, nobp]:")
    for T,k,s in zip(Tk2,kk2,sk2): print(f"  {T:6.1f} K : {k:.5f} +/- {s:.5f}")
    Tq2 = np.array([400,600,800,1000,1100.])  # nobp sweep spans 294..1200
    am2, asd2 = alpha_curve(Tk2, kk2, sk2, Tq2)
    print("isothermal temperature coefficient alpha(T)  [BP OFF]:")
    for T,a,s in zip(Tq2,am2,asd2): print(f"  alpha({T:.0f}K) = {a:7.2f} +/- {s:4.2f} pcm/K")
    # average coefficient over the operating range for each variant (pcm/K)
    a_on  = float(am.mean());  a_off = float(am2.mean())
    print(f"\nrange-avg alpha: BP-on {a_on:.2f} pcm/K, BP-off {a_off:.2f} pcm/K "
          f"(bracket [{min(a_on,a_off):.2f}, {max(a_on,a_off):.2f}])")

    # try beta_eff from prompt-only run if present
    beta_eff = 0.0065; beta_sig = 0.0
    try:
        import csv
        with open('runs/kin/keff.csv') as f:
            rows=list(csv.DictReader(f))
        kk_full = {float(r['T_K']):(float(r['keff']),float(r['keff_sigma']))
                   for r in rows if int(r['prompt_only'])==0}
        kk_pr   = {float(r['T_K']):(float(r['keff']),float(r['keff_sigma']))
                   for r in rows if int(r['prompt_only'])==1}
        T0=list(kk_pr.keys())[0]
        kf,sf=kk_full.get(T0,(None,None)); kp,sp=kk_pr[T0]
        if kf:
            beta_eff=1-kp/kf
            beta_sig=(kp/kf)*np.hypot(sf/kf,sp/kp)
            print(f"beta_eff (prompt method @ {T0}K) = {beta_eff:.5f} +/- {beta_sig:.5f}")
    except FileNotFoundError:
        print("beta_eff: prompt-only run not found; using 0.0065 (design-basis).")

    Top = 823.0   # core-avg graphite temp at 9 MW (30%), nominal ~550 C
    drho, kfun = TR.make_drho(Tk, kk, Top)

    # Nominal thermal parameters. Gcr/Grv are geometry-informed: radial graphite
    # conduction (k~40 W/m/K, core r~1.15 m, H=2.9 m) gives core->reflector
    # conductance of order 1-3 kW/K; reflector->vessel similar (conduction+gap
    # radiation). L0 is the passive (non-coolant) heat leak at the 30%-power test
    # condition, ~0.3 MW (< the 0.6 MW full-power VCS rating). See sources.md.
    base = dict(Top=Top, P0=9e6, Mc=14000.0, Mr=45000.0, Mv=100000.0,
                Gcr=2000.0, Grv=2500.0, Q0=0.3e6, L0=0.3e6,
                Ts=320.0, pexp=1.5, t_op=30*24*3600.0, Lam=1e-3,
                t_end=6.0*24*3600, S=1e-6)
    sol, beff = TR.run(base, drho, beta_eff)
    s0 = TR.summarize(sol, base['P0'], Top, drho)
    print("\n=== NOMINAL transient ===")
    print(f"  power min (first 30 min): {s0['Pmin_early']/1e3:.2f} kW at {s0['tmin']/60:.1f} min")
    print(f"  peak core temp: {s0['Tc_peak']-273:.0f} C at {s0['tpeak']/3600:.2f} h")
    print(f"  recriticality time: {s0['trec']/3600:.1f} h" if s0['trec'] else "  no recriticality")
    print(f"  stabilized fission power: {s0['P_stab']/1e3:.0f} kW ({s0['P_stab']/base['P0']*100:.1f}% of pre-trip 9MW)")
    print(f"  peak vessel temp: {s0['Tv_peak']-273:.0f} C (end {s0['Tv_end']-273:.0f} C)")

    # ---------- Sensitivity study (randomized over uncertain thermal params) ----------
    print("\n=== SENSITIVITY (random sample over thermal parameters) ===")
    NS = 400
    rows = []
    for _ in range(NS):
        Mc  = RNG.uniform(10000, 20000)
        Mr  = RNG.uniform(25000, 90000)     # responsive reflector graphite
        Gcr = RNG.uniform(3000, 12000)      # core<->reflector conductance
        Grv = RNG.uniform(2000, 8000)       # reflector<->vessel conductance
        L0  = RNG.uniform(0.3e6, 0.9e6)     # passive leak / VCS capacity
        pexp= RNG.uniform(1.0, 2.5)
        Topv= RNG.uniform(753., 893.)       # core-avg graphite temp at 9 MW
        top = RNG.uniform(3, 60)*24*3600.   # prior operating time
        p = dict(base); p.update(Mc=Mc,Mr=Mr,Gcr=Gcr,Grv=Grv,Q0=L0,L0=L0,
                                 pexp=pexp,Top=Topv,t_op=top)
        dr,_ = TR.make_drho(Tk, kk, Topv)
        try:
            so,_ = TR.run(p, dr, beta_eff)
            ss = TR.summarize(so, p['P0'], Topv, dr)
            rows.append((ss['trec']/3600 if ss['trec'] else np.nan,
                         ss['P_stab']/1e3, ss['Tc_peak']-273, ss['Tv_peak']-273))
        except Exception:
            continue
    G = np.array(rows)
    trec = G[:,0][~np.isnan(G[:,0])]; pstab=G[:,1]; tcpk=G[:,2]; tvpk=G[:,3]
    pc = lambda a,q: float(np.percentile(a,q))
    print(f"  recriticality time: median {np.median(trec):.1f} h, "
          f"P10-P90 [{pc(trec,10):.1f}, {pc(trec,90):.1f}] h (min {trec.min():.1f}, max {trec.max():.1f})")
    print(f"  stabilized fission power: median {np.median(pstab):.0f} kW, "
          f"[{pc(pstab,10):.0f}, {pc(pstab,90):.0f}] kW")
    print(f"  peak core graphite temp: median {np.median(tcpk):.0f} C, "
          f"[{pc(tcpk,10):.0f}, {pc(tcpk,90):.0f}] C, max {tcpk.max():.0f} C")
    print(f"  peak vessel temp: median {np.median(tvpk):.0f} C, max {tvpk.max():.0f} C")

    # ---------- Plot ----------
    fig, ax = plt.subplots(2,1, figsize=(8,7), sharex=True)
    t = sol.t/3600
    ax[0].plot(t, sol.y[0]/1e6, 'b'); ax[0].set_yscale('log')
    ax[0].set_ylabel('Fission power (MW)'); ax[0].grid(True, which='both', alpha=.3)
    ax[0].axhline(9,ls='--',c='gray',lw=.8); ax[0].set_ylim(1e-4,20)
    if s0['trec']: ax[0].axvline(s0['trec']/3600, ls=':', c='r', label=f"recrit {s0['trec']/3600:.1f} h")
    ax[0].legend(); ax[0].set_title('HTTR LOFC (9 MWt, all circulators trip, no scram, VCS on) — computed')
    ax[1].plot(t, sol.y[7]-273, 'r', label='core graphite (feedback)')
    ax[1].plot(t, sol.y[8]-273, 'orange', label='reflector')
    ax[1].plot(t, sol.y[9]-273, 'green', label='vessel (RPV)')
    ax[1].axhline(Top-273, ls='--', c='k', lw=.8, label=f'T_op {Top-273:.0f} C')
    ax[1].set_ylabel('Temperature (C)'); ax[1].set_xlabel('Time (h)')
    ax[1].grid(True, alpha=.3); ax[1].legend(); ax[1].set_xlim(0, 120)
    fig.tight_layout(); fig.savefig('output/lofc_transient.png', dpi=110)
    print("\nsaved output/lofc_transient.png")

    out = dict(k_T={float(T):[float(k),float(s)] for T,k,s in zip(Tk,kk,sk)},
               alpha_T={float(T):[float(a),float(s)] for T,a,s in zip(Tq,am,asd)},
               k_T_nobp={float(T):[float(k),float(s)] for T,k,s in zip(Tk2,kk2,sk2)},
               alpha_T_nobp={float(T):[float(a),float(s)] for T,a,s in zip(Tq2,am2,asd2)},
               alpha_bracket_pcmK=[min(a_on,a_off),max(a_on,a_off)],
               alpha_avg_on_pcmK=a_on, alpha_avg_off_pcmK=a_off,
               beta_eff=float(beta_eff), beta_eff_sigma=float(beta_sig),
               nominal=dict(Pmin_kW=float(s0['Pmin_early']/1e3),
                            tmin_min=float(s0['tmin']/60),
                            Tc_peak_C=float(s0['Tc_peak']-273),
                            tpeak_h=float(s0['tpeak']/3600),
                            trec_h=float(s0['trec']/3600) if s0['trec'] else None,
                            Pstab_kW=float(s0['P_stab']/1e3),
                            Tv_peak_C=float(s0['Tv_peak']-273),
                            Tv_end_C=float(s0['Tv_end']-273)),
               sens=dict(trec_h=[pc(trec,10),float(np.median(trec)),pc(trec,90),float(trec.min()),float(trec.max())],
                         Pstab_kW=[pc(pstab,10),float(np.median(pstab)),pc(pstab,90)],
                         Tcpeak_C=[pc(tcpk,10),float(np.median(tcpk)),pc(tcpk,90),float(tcpk.max())],
                         Tvpeak_C=[float(np.median(tvpk)),float(tvpk.max())]))
    json.dump(out, open('output/results.json','w'), indent=2)
    print("saved output/results.json")

if __name__ == '__main__':
    main()

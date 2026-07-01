"""
First-principles steady-state model of the passive RCCS natural-circulation loop.

Physics:
  (A) Loop momentum balance: buoyant driving head = friction + form losses  -> mdot
  (B) Energy balance: Q_air = mdot*cp*(T_out - T_in)
  (C) Cavity heat transfer: plate --(radiation + natural convection)--> riser surface
  (D) Riser internal forced/mixed convection: riser surface -> flowing air

Correlations (cited in calculation_note.md):
  - Dittus-Boelter (1930) turbulent internal convection: Nu=0.023 Re^0.8 Pr^0.4
  - Haaland (1983) friction factor
  - Catton (1978) vertical enclosure natural convection: Nu=0.046 Ra^(1/3)
  - Two-gray-surface radiation with reradiating walls (Incropera & DeWitt)
"""
import numpy as np
from scipy.optimize import brentq
import props as pr
import geom as G

SIGMA = 5.670374419e-8   # Stefan-Boltzmann

# ---------- Emissivities (inputs/02) ----------
EPS_PLATE = 0.78         # measured, SAE1020 mill-scale
EPS_RISER = 0.80         # oxidized ASTM A500 steel (not reported; assumed 0.7-0.85)

# ---------- Friction factor ----------
def fric(Re, rel_rough=6e-4):
    """Darcy friction factor. Laminar 64/Re; else Haaland (1983)."""
    Re = max(Re, 1.0)
    if Re < 2300:
        return 64.0/Re
    inv = -1.8*np.log10((rel_rough/3.7)**1.11 + 6.9/Re)
    return (1.0/inv)**2

# ---------- Loop pressure loss ----------
def loss(mdot, T_gm, T_out, T_amb, verbose=False):
    """Total loop pressure loss [Pa] at mass flow mdot [kg/s]."""
    parts = {}
    # Downcomer (cold, ambient air)
    rho_c = pr.rho(T_amb); mu_c = pr.mu(T_amb)
    V = mdot/(rho_c*G.A_dc)
    Re = rho_c*V*G.D_dc/mu_c
    f = fric(Re, 0.0002/G.D_dc)
    K_dc = 0.5 + 0.3            # entrance/flow-conditioner + 90 deg elbow
    parts['downcomer'] = (f*G.L_dc/G.D_dc + K_dc)*0.5*rho_c*V**2

    # Sudden expansion downcomer -> inlet plenum (exit loss)
    parts['plenum_in_expansion'] = 1.0*0.5*rho_c*V**2

    # Riser entrance (contraction from plenum into 12 tubes, re-entrant protrusion)
    rho_i = pr.rho(T_gm); mu_i = pr.mu(T_gm)
    Vr = mdot/(rho_i*G.A_flow_total)
    Rer = rho_i*Vr*G.Dh/mu_i
    fr = fric(Rer, 4.5e-5/G.Dh)
    K_ent = 0.5 + 0.5          # sudden contraction + re-entrant/sharp edge
    parts['riser_entrance'] = K_ent*0.5*rho_i*Vr**2

    # Riser friction (dominant)
    parts['riser_friction'] = fr*G.L_riser_total/G.Dh*0.5*rho_i*Vr**2

    # Riser exit into outlet plenum (sudden expansion)
    rho_o = pr.rho(T_out)
    Vro = mdot/(rho_o*G.A_flow_total)
    parts['riser_exit'] = 1.0*0.5*rho_o*Vro**2

    # Outlet plenum -> chimney ports (contraction + turn)
    mu_o = pr.mu(T_out)
    Vch = mdot/(rho_o*G.A_ch_total)
    Rech = rho_o*Vch*G.D_ch/mu_o
    fch = fric(Rech, 1.5e-4/G.D_ch)   # galvanized
    parts['plenum_out_to_chimney'] = 1.5*0.5*rho_o*Vch**2

    # Chimney friction (2 stacks) + elbows + dampers
    L_ch = G.L_ch_vert + G.L_ch_horiz
    K_ch = 2*0.5 + 5*0.2        # 2 elbows + 5 butterfly dampers (open ~0.2 each)
    parts['chimney_friction'] = (fch*L_ch/G.D_ch + K_ch)*0.5*rho_o*Vch**2

    # Chimney discharge (exit kinetic-energy loss)
    parts['chimney_exit'] = 1.0*0.5*rho_o*Vch**2

    tot = sum(parts.values())
    if verbose:
        for kk, vv in parts.items():
            print(f"    {kk:28s} {vv:8.3f} Pa  ({100*vv/tot:4.1f}%)")
        print(f"    Vr(riser)={Vr:.2f} m/s Re={Rer:.0f}  Vch={Vch:.2f} Vdc={V:.2f}")
    return tot, dict(Vr=Vr, Rer=Rer, fr=fr, Vch=Vch)

# ---------- Buoyant driving head ----------
def drive(T_gm, T_out, T_amb, H_riser=None, H_stack=None, dP_wind=0.0):
    """Buoyant driving pressure [Pa]. Reference column = outdoor ambient air."""
    if H_riser is None: H_riser = G.H_riser
    if H_stack is None: H_stack = G.H_stack_above_riser
    rho_amb = pr.rho(T_amb)
    rho_riser = pr.rho(T_gm)           # mean over heated riser
    rho_chim = pr.rho(T_out)           # ~T_out in insulated chimney/plenum
    dP = G.g*((rho_amb - rho_riser)*H_riser + (rho_amb - rho_chim)*H_stack)
    return dP + dP_wind

# ---------- Solve mass flow given Q ----------
def solve_flow(Q, T_in, T_amb, H_riser=None, H_stack=None, dP_wind=0.0):
    """Find mdot [kg/s] balancing buoyancy vs losses. Returns dict of results."""
    def residual(mdot):
        # inner iterate T_gm since cp depends on T
        T_out = T_in + Q/(mdot*pr.cp(T_in+30))
        for _ in range(20):
            T_gm = 0.5*(T_in+T_out)
            T_out_new = T_in + Q/(mdot*pr.cp(T_gm))
            if abs(T_out_new-T_out) < 1e-4: T_out = T_out_new; break
            T_out = T_out_new
        T_gm = 0.5*(T_in+T_out)
        dP_d = drive(T_gm, T_out, T_amb, H_riser, H_stack, dP_wind)
        dP_l, _ = loss(mdot, T_gm, T_out, T_amb)
        return dP_d - dP_l
    # bracket
    mdot = brentq(residual, 0.02, 20.0, xtol=1e-6)
    T_out = T_in + Q/(mdot*pr.cp(T_in+30))
    for _ in range(30):
        T_gm = 0.5*(T_in+T_out)
        T_out = T_in + Q/(mdot*pr.cp(T_gm))
    T_gm = 0.5*(T_in+T_out)
    dP_l, aux = loss(mdot, T_gm, T_out, T_amb)
    dP_d = drive(T_gm, T_out, T_amb, H_riser, H_stack, dP_wind)
    return dict(mdot=mdot, T_in=T_in, T_out=T_out, T_gm=T_gm, dT=T_out-T_in,
                dP=dP_d, **aux)

# ---------- Riser internal convection ----------
def h_internal(mdot, T_gm):
    """Internal convective coeff [W/m2K], Dittus-Boelter (turbulent) or laminar."""
    rho = pr.rho(T_gm); muv = pr.mu(T_gm); kv = pr.k(T_gm); Prv = pr.Pr(T_gm)
    Vr = mdot/(rho*G.A_flow_total)
    Re = rho*Vr*G.Dh/muv
    if Re > 4000:
        Nu = 0.023*Re**0.8*Prv**0.4                  # Dittus-Boelter, heating
        regime = 'turbulent'
    elif Re < 2300:
        Nu = 4.36                                     # laminar, const q'' (approx)
        regime = 'laminar'
    else:
        # transition: interpolate
        Nu = 4.36 + (0.023*4000**0.8*Prv**0.4-4.36)*(Re-2300)/1700
        regime = 'transition'
    h = Nu*kv/G.Dh
    return h, Re, Nu, regime

# ---------- Cavity natural convection (vertical enclosure) ----------
def h_cavity(T_p, T_r):
    """Natural-convection coeff across the plate->riser air gap [W/m2K]."""
    T_f = 0.5*(T_p+T_r)
    L = G.cavity_depth
    beta = pr.beta(T_f); nu = pr.nu(T_f); kv = pr.k(T_f)
    alpha = kv/(pr.rho(T_f)*pr.cp(T_f)); Prv = pr.Pr(T_f)
    dT = max(T_p-T_r, 1e-3)
    Ra = G.g*beta*dT*L**3/(nu*alpha)
    # Catton (1978) vertical cavity, high Ra:
    Nu = max(1.0, 0.046*Ra**(1.0/3.0))
    h = Nu*kv/L
    return h, Ra, Nu

# ---------- Cavity radiation (two-gray-surface, reradiating walls) ----------
def q_rad(T_p, T_r):
    """Net radiative heat plate->risers [W]. Parallel-plate w/ reradiating cavity."""
    denom = 1.0/EPS_PLATE + 1.0/EPS_RISER - 1.0
    return SIGMA*G.A_plate*(T_p**4 - T_r**4)/denom

# ---------- Circumferential wall conduction (one riser, mid-plane) ----------
def circumferential_wall(Q, hi, T_gm, frac, N=240):
    """Solve steady conduction around one riser's wall cross-section.
    Balance per node: k*t*(Ti-1+Ti+1-2Ti)/ds + q''_ext*ds - hi*ds*(Ti-T_gm)=0.
    Returns face temperatures [K]."""
    kw, tw = 50.0, G.wall_t
    # outer perimeter geometry (front narrow, side wide, rear narrow, side wide)
    Lf, Ls, Lr = G.r_out_b, G.r_out_a, G.r_out_b   # 2in, 10in, 2in outer
    P = 2*(Lf+Ls)
    ds = P/N
    # arc-length boundaries of each face (start at front center, go around)
    # order: front(half) side rear side front(half)
    # simpler: build face label per node by cumulative length
    seg = [('front',Lf),('side',Ls),('rear',Lr),('side',Ls)]
    labels = []
    acc = 0.0
    bounds=[]
    x=0.0
    for name,L in seg:
        bounds.append((name,x,x+L)); x+=L
    s = (np.arange(N)+0.5)*ds
    labels = []
    for si in s:
        for name,a,b in bounds:
            if a<=si<b: labels.append(name); break
        else: labels.append('side')
    labels=np.array(labels)
    # per-face heat -> flux [W/m2] over outer area of that face type (all risers, heated L)
    A = dict(front=G.N_RISER*Lf*G.L_riser_heated,
             side =G.N_RISER*(2*Ls)*G.L_riser_heated,
             rear =G.N_RISER*Lr*G.L_riser_heated)
    qpp = dict(front=frac['front']*Q/A['front'],
               side =2*frac['side']*Q/A['side'],   # frac['side'] is per single side
               rear =frac['rear']*Q/A['rear'])
    qext = np.array([qpp[l] for l in labels])
    # assemble periodic tridiagonal system  M T = b
    a_cond = kw*tw/ds
    M = np.zeros((N,N)); b = np.zeros(N)
    for i in range(N):
        ip, im = (i+1)%N, (i-1)%N
        M[i,i]   = -2*a_cond - hi*ds
        M[i,ip] += a_cond
        M[i,im] += a_cond
        b[i]     = -qext[i]*ds - hi*ds*T_gm
    T = np.linalg.solve(M, b)
    out = dict(front=T[labels=='front'].mean(),
               side =T[labels=='side'].mean(),
               rear =T[labels=='rear'].mean(),
               mean =T.mean())
    return out

# ---------- Full steady solve: given Q, find all temps & flow ----------
def steady(Q, T_in, T_amb, **kw):
    fl = solve_flow(Q, T_in, T_amb, **kw)
    T_gm = fl['T_gm']
    hi, Re_i, Nu_i, regime = h_internal(fl['mdot'], T_gm)

    # Mean riser surface temp from internal convection (wall conduction negligible):
    # Q = hi * A_inner_total * (T_r_mean - T_gm)
    T_r_mean = T_gm + Q/(hi*G.A_riser_inner_total)

    # Plate temp: solve Q = q_rad(T_p,T_r) + h_cav*A_plate*(T_p-T_r), with T_r=T_r_mean
    def fp(T_p):
        hc, Ra, Nu = h_cavity(T_p, T_r_mean)
        return q_rad(T_p, T_r_mean) + hc*G.A_plate*(T_p-T_r_mean) - Q
    T_p = brentq(fp, T_r_mean+1, T_r_mean+2000)
    hc, Ra_c, Nu_c = h_cavity(T_p, T_r_mean)
    Qr = q_rad(T_p, T_r_mean)
    Qc = hc*G.A_plate*(T_p-T_r_mean)

    # ---- Circumferential wall-conduction model at mid-plane (reporting location) ----
    # Heat lands mostly on the front face (line-of-sight to plate); the conductive
    # steel tube spreads it around the perimeter, all of which convects to the gas.
    # Face heat fractions (assumption; front-dominated because radiation is line-of-sight):
    frac = dict(front=0.80, side=0.075, rear=0.05)   # front + 2*side + rear = 1.0
    Tw = circumferential_wall(Q, hi, T_gm, frac)
    T_rf_mid = Tw['front']     # hot (front) face temp at mid-plane

    return dict(Q=Q, **fl, hi=hi, Re_i=Re_i, Nu_i=Nu_i, regime=regime,
                T_r_mean=T_r_mean, T_p=T_p, hc=hc, Ra_c=Ra_c,
                Qrad=Qr, Qconv=Qc, frad=Qr/(Qr+Qc),
                T_rf_mid=T_rf_mid, Tw_front=Tw['front'], Tw_side=Tw['side'],
                Tw_rear=Tw['rear'], Tw_mean=Tw['mean'])

def report(res, title=""):
    print(f"\n=== {title} ===")
    print(f"  Q_air              = {res['Q']/1000:.2f} kW")
    print(f"  mass flow  mdot    = {res['mdot']:.4f} kg/s  = {res['mdot']*60:.2f} kg/min")
    print(f"  riser air dT       = {res['dT']:.1f} K   (T_in {res['T_in']-273.15:.1f} -> T_out {res['T_out']-273.15:.1f} C)")
    print(f"  driving head dP    = {res['dP']:.2f} Pa")
    print(f"  riser V, Re        = {res['Vr']:.2f} m/s, {res['Rer']:.0f}  ({res['regime']})")
    print(f"  h_internal         = {res['hi']:.2f} W/m2K  (Nu={res['Nu_i']:.1f})")
    print(f"  riser surf T (mean)= {res['T_r_mean']-273.15:.1f} C")
    print(f"  riser front T @mid = {res['T_rf_mid']-273.15:.1f} C")
    print(f"  plate front T      = {res['T_p']-273.15:.1f} C")
    print(f"  cavity h_conv      = {res['hc']:.2f} W/m2K (Ra={res['Ra_c']:.2e})")
    print(f"  Q_rad / Q_conv     = {res['Qrad']/1000:.2f} / {res['Qconv']/1000:.2f} kW")
    print(f"  radiative fraction = {res['frad']*100:.1f} %")
    return res

if __name__ == "__main__":
    # Case 1 baseline: heat to air ~56 kW (scaled peak duty), T_in=20C, outdoor +2C
    print("Loss breakdown at trial mdot=1.0 kg/s, T_gm=340K, T_out=360K, T_amb=275K:")
    loss(1.0, 340, 360, 275.15, verbose=True)
    for Q in [56.07e3, 70e3, 82e3]:
        report(steady(Q, 20+273.15, 2+273.15), f"Case1  Q_air={Q/1000:.1f} kW")

"""
Reduced (0-D/1-D) physics model of the RCCS natural-circulation loop.

Couples:
  (A) Loop momentum balance  : buoyant draft = friction + form losses  -> mass flow
  (B) Energy balance         : Q = m_dot cp (Tout - Tin)               -> air dT
  (C) Cavity heat transfer   : Q = radiation(plate<->riser) + cavity natural convection
                                                                        -> plate & riser wall T
  (D) Internal convection    : Q = h_int A_int (Twall - Tair)          -> wall/air coupling

Correlations cited inline. SI units, T in K unless suffixed _C.
"""
import numpy as np
from scipy.optimize import brentq
import props as pr
import geom as g

sigma = 5.670374419e-8

# ---------------------------------------------------------------------------
# (A) LOOP PRESSURE LOSSES
# ---------------------------------------------------------------------------
def darcy_f(Re, eps_rel=0.0):
    """Darcy friction factor. Laminar 64/Re; turbulent Petukhov/Blasius blend."""
    if Re < 1e-6:
        return 0.0
    if Re < 2300:
        return 64.0/Re
    if Re < 4000:  # transition: linear blend
        fl = 64.0/2300
        ft = (0.790*np.log(4000)-1.64)**-2
        return fl + (ft-fl)*(Re-2300)/1700
    return (0.790*np.log(Re)-1.64)**-2   # Petukhov, smooth

def loop_losses(mdot, Tin, Tout, Tamb):
    """Sum of friction + form pressure losses [Pa] around the loop for given mdot."""
    Tm_riser = 0.5*(Tin+Tout)
    # --- riser (dominant): 12 parallel ducts
    rho_r = pr.rho(Tm_riser); mu_r = pr.mu(Tm_riser)
    V_r = mdot/(rho_r*g.A_RISER)
    Re_r = rho_r*V_r*g.DH_RISER/mu_r
    f_r = darcy_f(Re_r)
    dP_r_fric = f_r*(g.L_RISER_TOT/g.DH_RISER)*0.5*rho_r*V_r**2
    # form: riser inlet contraction (~0.5) + exit expansion (~1.0)
    K_riser_form = 0.5+1.0
    dP_r_form = K_riser_form*0.5*rho_r*V_r**2
    # --- chimney (two 24-in stacks in parallel)
    rho_c = pr.rho(Tout); mu_c = pr.mu(Tout)
    V_c = mdot/(rho_c*g.A_CHIM)
    Re_c = rho_c*V_c*g.D_CHIM/mu_c
    f_c = darcy_f(Re_c)
    dP_c_fric = f_c*(g.L_CHIM_EQ/g.D_CHIM)*0.5*rho_c*V_c**2
    # chimney entrance (turn+contraction from plenum) + discharge exit
    K_chim_form = 1.5+1.0
    dP_c_form = K_chim_form*0.5*rho_c*V_c**2
    # --- downcomer (single 24-in, cold air)
    rho_d = pr.rho(Tin); mu_d = pr.mu(Tin)
    V_d = mdot/(rho_d*g.A_DOWN)
    Re_d = rho_d*V_d*g.D_DOWN/mu_d
    f_d = darcy_f(Re_d)
    dP_d_fric = f_d*(g.L_DOWN_EQ/g.D_DOWN)*0.5*rho_d*V_d**2
    # downcomer entrance + flow conditioner + 90 elbow
    K_down_form = 0.5+0.5+0.9
    dP_d_form = K_down_form*0.5*rho_d*V_d**2
    # --- plena expansion/contraction losses (lumped, based on riser velocity)
    dP_plena = 1.0*0.5*rho_r*V_r**2
    total = (dP_r_fric+dP_r_form+dP_c_fric+dP_c_form+dP_d_fric+dP_d_form+dP_plena)
    detail = dict(V_r=V_r, Re_r=Re_r, f_r=f_r, V_c=V_c, Re_c=Re_c, V_d=V_d,
                  dP_r_fric=dP_r_fric, dP_r_form=dP_r_form,
                  dP_c=dP_c_fric+dP_c_form, dP_d=dP_d_fric+dP_d_form, dP_plena=dP_plena)
    return total, detail

def draft(Tin, Tout, Tamb):
    """Buoyant driving pressure [Pa].
    dP = g*[ rho_amb*H - integral(rho_int dz) ], intake at plenum (z=0),
    risers 0..Ztop (linear Tin->Tout), chimney Ztop..H at Tout.
    rho_amb evaluated at OUTDOOR temperature (external stack reference)."""
    rho_amb = pr.rho(Tamb)
    Ztop = g.Z_RISER_TOP
    H = g.Z_DISCHARGE
    # riser column integral of rho over 0..Ztop with linear T
    nseg = 40
    zr = np.linspace(0, Ztop, nseg)
    Tr = Tin + (Tout-Tin)*zr/Ztop
    int_riser = np.trapezoid(pr.rho(Tr), zr)
    # chimney column Ztop..H at Tout
    int_chim = pr.rho(Tout)*(H-Ztop)
    int_int = int_riser+int_chim
    return pr.G*(rho_amb*H - int_int)

# ---------------------------------------------------------------------------
# (B)+(A) SOLVE MASS FLOW for given net heat Q
# ---------------------------------------------------------------------------
def solve_flow(Q, Tin_C=20.0, Tamb_C=2.0, wind=0.0, K_wind=0.0):
    """Solve natural-circulation mass flow [kg/s] balancing draft=losses.
    Q [W] net heat into air. Returns dict."""
    Tin = Tin_C+273.15; Tamb = Tamb_C+273.15
    def outlet(mdot):
        Tout = Tin + Q/(mdot*pr.cp(Tin))
        for _ in range(3):                       # converge mean-cp
            cpm = pr.cp(0.5*(Tin+min(Tout,1200.0)))
            Tout = Tin + Q/(mdot*cpm)
        return min(Tout,1200.0)
    def residual(mdot):
        Tout = outlet(mdot)
        dP_drive = draft(Tin, Tout, Tamb)
        dP_loss, _ = loop_losses(mdot, Tin, Tout, Tamb)
        dP_wind = K_wind*0.5*pr.rho(Tamb)*wind**2   # adverse gust at discharge
        return dP_drive - dP_loss - dP_wind
    mdot = brentq(residual, 0.02, 5.0, xtol=1e-7)
    Tout = outlet(mdot)
    dT = Tout-Tin
    dP_drive = draft(Tin, Tout, Tamb)
    dP_loss, det = loop_losses(mdot, Tin, Tout, Tamb)
    return dict(mdot=mdot, mdot_kgmin=mdot*60, Tin_C=Tin_C, Tout_C=Tout-273.15,
                dT=dT, dP_drive=dP_drive, dP_loss=dP_loss, Tamb_C=Tamb_C, Q=Q, **det)

# ---------------------------------------------------------------------------
# (D) INTERNAL FORCED/MIXED CONVECTION in risers
# ---------------------------------------------------------------------------
def h_internal(mdot, Tin, Tout):
    Tm = 0.5*(Tin+Tout)
    rho=pr.rho(Tm); mu=pr.mu(Tm); k=pr.k_air(Tm); Prn=pr.Pr(Tm)
    V=mdot/(rho*g.A_RISER); Re=rho*V*g.DH_RISER/mu
    if Re>4000:
        f=(0.790*np.log(Re)-1.64)**-2
        Nu=(f/8)*(Re-1000)*Prn/(1+12.7*np.sqrt(f/8)*(Prn**(2/3)-1))  # Gnielinski
        corr="Gnielinski"
    elif Re<2300:
        # laminar, constant-q, rectangular duct aspect ~5.9 -> Nu_H ~ 5.3; entrance raises it
        Nu=5.3; corr="laminar rect (Nu_H~5.3)"
    else:
        Nu=5.3+(( (0.790*np.log(4000)-1.64)**-2/8)*(4000-1000)*Prn/
                (1+12.7*np.sqrt((0.790*np.log(4000)-1.64)**-2/8)*(Prn**(2/3)-1))-5.3)*(Re-2300)/1700
        corr="transition"
    h=Nu*k/g.DH_RISER
    return dict(h=h, Nu=Nu, Re=Re, V=V, corr=corr)

# ---------------------------------------------------------------------------
# (C) CAVITY: radiation + natural convection between plate and riser plane
# ---------------------------------------------------------------------------
def h_cavity(Tp, Tr):
    """Natural convection in the vertical air cavity (hot plate <-> cold riser wall).
    Catton correlation for vertical rectangular enclosures (Bejan 'Convection HT').
    L = gap, H = cavity height."""
    L=g.CAV_GAP; H=g.CAV_H
    Tmean=0.5*(Tp+Tr)
    beta=1/Tmean; nu=pr.nu(Tmean); al=pr.alpha(Tmean); k=pr.k_air(Tmean); Prn=pr.Pr(Tmean)
    dT=abs(Tp-Tr)
    Ra=pr.G*beta*dT*L**3/(nu*al)
    HL=H/L
    # Catton (2<H/L<10): Nu = 0.22 (Pr/(0.2+Pr) Ra)^0.28 (H/L)^-0.25
    Nu = 0.22*(Prn/(0.2+Prn)*Ra)**0.28*(HL)**-0.25
    Nu=max(Nu,1.0)
    h=Nu*k/L
    return dict(h=h, Nu=Nu, Ra=Ra)

def rad_plate_riser(Tp, Tr):
    """Net radiative exchange plate<->riser plane [W], gray-diffuse parallel surfaces
    with re-radiating adiabatic side/back walls. Area ~ plate area, F_eff~0.9."""
    eps_p=g.EPS_PLATE; eps_r=g.EPS_RISER; A=g.A_PLATE
    F=0.90  # facing view factor plate->riser plane incl. reradiating walls (assumption)
    # network resistance (equal areas approx A_p=A_r=A)
    denom=(1-eps_p)/(eps_p*A)+1/(A*F)+(1-eps_r)/(eps_r*A)
    Q=sigma*(Tp**4-Tr**4)/denom
    return Q

def solve_cavity(Q, mdot, Tin_C, Tout_C):
    """Given net heat Q and flow, solve plate temp Tp and riser wall temp Tr.
    Two equations:
       Q = Q_rad(Tp,Tr) + h_cav*A_plate*(Tp-Tr)        (plate -> riser plane)
       Q = h_int*A_int*(Tr_in - Tair_mean)             (riser -> internal air)
    thin steel wall: Tr_out ~ Tr_in = Tr.
    """
    Tin=Tin_C+273.15; Tout=Tout_C+273.15
    Tair_mean=0.5*(Tin+Tout)
    hi=h_internal(mdot,Tin,Tout); h_int=hi['h']
    # riser wall temp from internal convection (uses full internal wetted area)
    Tr = Tair_mean + Q/(h_int*g.A_INT_WET)
    # plate temp: solve Q = Qrad(Tp,Tr)+hcav*A*(Tp-Tr)
    def f(Tp):
        hc=h_cavity(Tp,Tr)['h']
        return rad_plate_riser(Tp,Tr)+hc*g.A_PLATE*(Tp-Tr)-Q
    Tp=brentq(f,Tr+1,Tr+1500)
    hc=h_cavity(Tp,Tr)
    Qrad=rad_plate_riser(Tp,Tr)
    Qconv_cav=hc['h']*g.A_PLATE*(Tp-Tr)
    return dict(Tp_C=Tp-273.15, Tr_mean_C=Tr-273.15, Tair_mean_C=Tair_mean-273.15,
                h_int=h_int, Nu_int=hi['Nu'], Re_int=hi['Re'], V_int=hi['V'], corr=hi['corr'],
                h_cav=hc['h'], Ra_cav=hc['Ra'], Qrad=Qrad, Qconv_cav=Qconv_cav,
                frac_rad=Qrad/Q, Tr=Tr, Tp=Tp)

def riser_perimeter(Q, cav, mdot, Tin_C, Tout_C, zfrac=0.5,
                    split=(0.70,0.12,0.12,0.06)):
    """Solve the circumferential temperature distribution of ONE riser tube wall at
    axial station z (zfrac of heated height) with a 1-D fin (perimeter conduction)
    model:  k t d2T/ds2 + q_ext(s) - h_int (T - T_air_local) = 0, periodic in s.

    The external heat is applied per face: radiation Q_rad split (front,sideN,sideS,rear)
    by 'split'; cavity convection Q_conv distributed uniformly over outer perimeter.
    Returns front-face and mean wall temperature and the per-face received flux.
    Wall spreads heat circumferentially -> front hot spot is bounded, not the naive
    q/h value."""
    Tin=Tin_C+273.15; Tout=Tout_C+273.15
    Tair=Tin+(Tout-Tin)*zfrac
    hi=h_internal(mdot,Tin,Tout); h_int=hi['h']
    t=g.WALL_RISER; k=g.K_STEEL
    # perimeter faces in physical order: front(narrow) -> side(wide) -> rear(narrow)
    # -> side(wide) -> (wrap to front). widths(m) and radiative split fractions.
    w   =[2.0*g.IN, 10.0*g.IN, 2.0*g.IN, 10.0*g.IN]
    spl =[split[0], split[1], split[3], split[2]]   # front, side, rear, side
    Ptot=sum(w)
    # per-tube axial-linear heat density at this station (uniform axial profile):
    qrad_tube=cav['Qrad']/g.N_RISER/g.L_HEAT      # W/m axial (radiative)
    qconv_tube=cav['Qconv_cav']/g.N_RISER/g.L_HEAT
    # uniform grid over the full perimeter
    N=400; ds=Ptot/N
    # cumulative face boundaries to classify each node
    bnd=np.cumsum(w); face_of=np.zeros(N,dtype=int); qext=np.zeros(N)
    for i in range(N):
        s=(i+0.5)*ds
        fi=int(np.searchsorted(bnd, s, side='right')); fi=min(fi,3)
        face_of[i]=fi
        qflux_rad = spl[fi]*qrad_tube/w[fi]       # W/m2 radiative on this face
        qflux_conv= qconv_tube/Ptot               # W/m2 uniform cavity convection
        qext[i]=qflux_rad+qflux_conv
    A=np.zeros((N,N)); b=np.zeros(N)
    c=k*t/ds**2
    for i in range(N):
        A[i,i]=-2*c-h_int
        A[i,(i+1)%N]=c
        A[i,(i-1)%N]=c
        b[i]=-qext[i]-h_int*Tair
    T=np.linalg.solve(A,b)
    Tfront=np.mean(T[face_of==0]); Tside=np.mean(T[face_of==1])
    Trear =np.mean(T[face_of==2]); Tmean=np.mean(T)
    # per-face received flux (radiative), for radiative-fraction-by-face reporting
    return dict(Tfront_C=Tfront-273.15, Trear_C=Trear-273.15, Tside_C=Tside-273.15,
                Twall_mean_C=Tmean-273.15, Tair_local_C=Tair-273.15,
                q_front=split[0]*qrad_tube/w[0]+qconv_tube/Ptot)

# ---------------------------------------------------------------------------
def full_case(Q, Tin_C=20.0, Tamb_C=2.0, wind=0.0, K_wind=0.0, label=""):
    fl=solve_flow(Q,Tin_C,Tamb_C,wind,K_wind)
    cav=solve_cavity(Q, fl['mdot'], Tin_C, fl['Tout_C'])
    ff=riser_perimeter(Q,cav,fl['mdot'],Tin_C,fl['Tout_C'])
    out=dict(label=label, **fl); out.update(cav); out.update(ff)
    return out

if __name__=="__main__":
    r=full_case(56000.0, Tin_C=20, Tamb_C=2, label="Case1 baseline 56kW")
    print("=== Case 1 baseline (Q_net=56 kW) ===")
    print(f"mdot        = {r['mdot']:.4f} kg/s = {r['mdot_kgmin']:.2f} kg/min")
    print(f"V_riser     = {r['V_r']:.3f} m/s  Re_riser={r['Re_r']:.0f}")
    print(f"Tin/Tout    = {r['Tin_C']:.1f} / {r['Tout_C']:.1f} C   dT={r['dT']:.1f} K")
    print(f"draft/loss  = {r['dP_drive']:.2f} / {r['dP_loss']:.2f} Pa")
    print(f"Plate Tp    = {r['Tp_C']:.1f} C")
    print(f"Riser wall   : mean={r['Twall_mean_C']:.1f}C front={r['Tfront_C']:.1f}C side={r['Tside_C']:.1f}C rear={r['Trear_C']:.1f}C (z=3.5m)")
    print(f"h_int       = {r['h_int']:.2f} W/m2K ({r['corr']}, Nu={r['Nu_int']:.1f})")
    print(f"h_cav       = {r['h_cav']:.2f} W/m2K  Ra_cav={r['Ra_cav']:.2e}")
    print(f"Q_rad/Q_conv= {r['Qrad']/1e3:.2f} / {r['Qconv_cav']/1e3:.2f} kW  rad frac={r['frac_rad']:.2%}")

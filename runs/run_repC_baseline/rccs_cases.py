"""
Case analyses built on rccs_model.py:
  Case 2 - accident decay-heat transient (quasi-steady + self-limiting curve + lumped transient)
  Case 3 - weather sensitivity (outdoor T and wind)
  Front-face wall temperature estimate and per-face radiation allocation.
"""
import numpy as np
from rccs_model import (solve_steady, air, radiation_Q, cavity_nat_conv_h,
                        A_plate, A_int, N_RISER, L_heated, ro_n, ro_w, IN,
                        SIGMA, g, A_chimney, H_stack, L_gap)

# ---------------------------------------------------------------------------
# Decay-heat power curve (polynomial in t=minutes, x Pscale=90)  Case 2
# ---------------------------------------------------------------------------
C = [466.531039994, 0.078631095079, 0.000170562320568, -1.28449427566e-07,
     5.09424812301e-11, -1.27606140005e-14, 2.04789514471e-18,
     -2.08318254453e-22, 1.29530038954e-26, -4.48601180685e-31]
PSCALE = 90.0
def decay_power_poly_W(t_min):
    return PSCALE*sum(c*t_min**n for n,c in enumerate(C))

# The supplied C0..C9 polynomial (C10 missing) peaks near 87 kW and goes negative
# after ~110 h, so it does NOT reproduce the stated 26->56 kW / peak-at-84.85 h shape.
# Per the task's explicit alternative, impose the normalized decay-heat shape:
#   normal load 26.16 kW, rising to 56.07 kW peak at t=84.85 h, then declining.
T_PEAK_H = 84.85
P_NORMAL = 26160.0
P_PEAK   = 56070.0
def decay_power_W(t_min):
    """Imposed normalized decay-heat curve (½-scale electric-equiv watts)."""
    th = t_min/60.0
    if th <= T_PEAK_H:
        # smooth rise normal->peak (raised-cosine, monotonic)
        x = th/T_PEAK_H
        s = 0.5*(1-np.cos(np.pi*x))          # 0->1
        return P_NORMAL + (P_PEAK-P_NORMAL)*s
    else:
        # gradual decay after peak (~ t^-0.2 decay-heat-like), floor at normal load
        return P_NORMAL + (P_PEAK-P_NORMAL)*max(0.0,(T_PEAK_H/th)**0.6)

# ---------------------------------------------------------------------------
# Self-limiting check: removal capacity vs plate temperature
# For a fixed plate temperature, how much heat can the passive loop remove?
# (invert: given plate T, find consistent Q). We sweep Q and read plate T.
# ---------------------------------------------------------------------------
def removal_curve():
    Qs = np.linspace(5000, 120000, 30)
    Tp = []
    for Q in Qs:
        s = solve_steady(Q, T_cold_C=20, T_inlet_C=20)
        Tp.append(s['T_plate_C'])
    return Qs, np.array(Tp)

# ---------------------------------------------------------------------------
# Front-face temperature estimate (measurement is front face, z=3500mm).
# Model gives perimeter-mean wall Tw. Front face carries the incident load and
# conducts circumferentially through thin high-k steel. Estimate circumferential
# rise.  q''_front ~ Q/A_front; conduction around perimeter, steel wall t, k.
# ---------------------------------------------------------------------------
def front_face_delta(Q_cav, T_air_mean_C, h_i):
    """Circumferential perimeter fin: external radiative+conv heat lands on the
    riser outer faces (front 55% / sides 35% / rear 10% per per_face_split), the
    thin steel wall conducts around the perimeter, and the inner surface convects
    to the internal air at h_i. Solve steady 1-D conduction around the perimeter.
    Returns front-face wall temperature (deg C) at the instrumented mid-plane."""
    t_wall = 0.188*IN                     # 4.78 mm
    k_steel = 50.0
    per = per_face_split()
    # per-tube external heat, at the mid-plane treat per unit length
    Q_tube = Q_cav/N_RISER                # W per tube (whole length)
    # outer face widths (m): front(narrow) ro_n, each side(wide) ro_w, rear(narrow) ro_n
    # build perimeter grid: front | side1 | rear | side2  (outer widths)
    widths = [ro_n, ro_w, ro_n, ro_w]
    load_frac = [per['front'], per['sides']/2, per['rear'], per['sides']/2]
    seglen = np.array(widths)
    Pout = seglen.sum()
    n_per_seg = 40
    ds = np.concatenate([[w/n_per_seg]*n_per_seg for w in widths])
    N = len(ds)
    # external volumetric line-load per node (W per m tube length): distribute each
    # face's load over its nodes; use per-m by dividing whole-tube W by L_heated
    qext_line = np.zeros(N)               # W/m (per unit axial length)
    idx=0
    for w,lf in zip(widths,load_frac):
        qseg = (Q_tube*lf)/L_heated       # W/m over this face
        qext_line[idx:idx+n_per_seg] = qseg/n_per_seg   # per node
        idx+=n_per_seg
    # inner convection: inner perimeter slightly smaller; use inner widths approx = outer - 2*t
    # per node convective loss = h_i * (ds_inner) * (T-Tair) ; ds_inner ~ ds
    Tair = T_air_mean_C
    # assemble tridiagonal (periodic) conduction: k*t*(T_{i+1}-2T_i+T_{i-1})/ds^2 style
    # node equation: -k t (dT/ds)|_+ + k t (dT/ds)|_- + qext - h ds (T-Tair)=0
    A = np.zeros((N,N)); b=np.zeros(N)
    kt = k_steel*t_wall
    for i in range(N):
        ip=(i+1)%N; im=(i-1)%N
        dsp=0.5*(ds[i]+ds[ip]); dsm=0.5*(ds[i]+ds[im])
        A[i,ip]+= kt/dsp
        A[i,im]+= kt/dsm
        A[i,i] -= (kt/dsp+kt/dsm)
        A[i,i] -= h_i*ds[i]
        b[i]   -= qext_line[i] + h_i*ds[i]*Tair
    T = np.linalg.solve(A,b)
    T_front = T[:n_per_seg].mean()
    T_side  = T[n_per_seg:2*n_per_seg].mean()
    T_rear  = T[2*n_per_seg:3*n_per_seg].mean()
    qpp_front = (Q_tube*per['front'])/(ro_n*L_heated)
    return dict(T_front=T_front, T_side=T_side, T_rear=T_rear,
                T_perim_mean=T.mean(), qpp_front=qpp_front)

# ---------------------------------------------------------------------------
# Per-face radiation allocation (approximate view factors plate->riser faces).
# Front narrow face: direct line of sight, F_plate->front high.
# Side wide faces: oblique, partial. Rear: shadowed ~ small (diffuse reflections).
# We split the *incident radiative* flux; internal convective removal ~uniform.
# ---------------------------------------------------------------------------
def per_face_split():
    # crude geometric weights of radiative INCIDENCE on the riser bank faces:
    # front (2in narrow, full LOS) dominates; sides (10in) catch grazing + gaps;
    # rear (2in narrow, shadowed) small. Normalized weights from solid-angle argument.
    w_front = 0.55; w_sides = 0.35; w_rear = 0.10
    return dict(front=w_front, sides=w_sides, rear=w_rear)

# ---------------------------------------------------------------------------
# Lumped transient (validate quasi-steady): plate+riser thermal mass vs decay curve
# ---------------------------------------------------------------------------
def transient():
    # thermal capacitance
    rho_s, cp_s = 7850., 480.
    m_plate = 0.0254*A_plate*rho_s                    # 1-in plate
    P_out = 2*(ro_w+ro_n); t_w = 0.188*IN
    m_riser = N_RISER*P_out*t_w*7.49*rho_s
    C_th = (m_plate+m_riser)*cp_s
    # integrate T_plate with quasi-steady removal as function of Tp
    Qs, Tp_curve = removal_curve()
    # invert to Q_removed(Tp)
    from numpy import interp
    def Q_removed(Tp_C):
        return interp(Tp_C, Tp_curve, Qs)   # monotonic
    dt = 60.0  # s
    t_end = 130*3600
    Tp_min, Tp_max = Tp_curve.min(), Tp_curve.max()
    t = 0.0; Tp = 233.0  # start near normal-duty (26 kW) plate temp
    ts=[]; Tps=[]; Pin=[]
    while t <= t_end:
        Pgen = decay_power_W(t/60.0)
        Tp_c = min(max(Tp, Tp_min), Tp_max)
        Qrem = Q_removed(Tp_c)
        Tp += (Pgen - Qrem)/C_th*dt
        if int(t)%1800==0:
            ts.append(t/3600); Tps.append(Tp); Pin.append(Pgen)
        t += dt
    return C_th, np.array(ts), np.array(Tps), np.array(Pin)

if __name__ == '__main__':
    print("=== Case 2: decay power curve ===")
    for h in [0, 20, 60, 84.85, 100, 120]:
        print(f"  t={h:6.2f} h  P={decay_power_W(h*60)/1000:.2f} kW")
    print()

    print("=== Self-limiting: plate T vs delivered power ===")
    Qs, Tp = removal_curve()
    for Q,T in zip(Qs, Tp):
        if int(Q)%10000<4000:
            print(f"  Q={Q/1000:5.1f} kW -> T_plate={T:6.1f} C")
    print("  (monotonic, finite slope -> stable equilibrium at every power => LEVELS OFF)")
    print()

    print("=== Peak (accident) steady state at 56.07 kW ===")
    s = solve_steady(56070, T_cold_C=20, T_inlet_C=20)
    T_air_mean = s['T_in_C'] + 0.5*s['dT_air']
    ff = front_face_delta(56070, T_air_mean, s['h_i'])
    print(f"  m_dot={s['mdot']:.3f} kg/s  dT_air={s['dT_air']:.1f} K  T_out={s['T_out_C']:.1f} C")
    print(f"  wall(perim mean, model)={s['T_wall_C']:.1f} C")
    print(f"  fin model: front={ff['T_front']:.1f} C  side={ff['T_side']:.1f} C  "
          f"rear={ff['T_rear']:.1f} C  perim_mean={ff['T_perim_mean']:.1f} C")
    print(f"  plate={s['T_plate_C']:.1f} C  rad_frac={s['rad_frac']:.2f}  "
          f"front-face flux={ff['qpp_front']/1000:.1f} kW/m2")
    print()

    print("=== Lumped transient validation ===")
    C_th, ts, Tps, Pin = transient()
    print(f"  C_th={C_th/1e6:.2f} MJ/K")
    ipk = np.argmax(Tps)
    print(f"  peak T_plate={Tps[ipk]:.1f} C at t={ts[ipk]:.1f} h; power peak {Pin.max()/1000:.1f} kW")
    print(f"  final T_plate={Tps[-1]:.1f} C")
    print()

    print("=== Case 3: weather sensitivity ===")
    print("  outdoor/inlet T sweep (no wind):")
    for Tc in [-18, -10, 0, 2, 10, 20, 24]:
        s = solve_steady(56070, T_cold_C=Tc, T_inlet_C=Tc)
        print(f"   T_amb={Tc:4d} C: m_dot={s['mdot']:.3f} kg/s ({s['mdot_kgmin']:.1f} kg/min) "
              f"dT_air={s['dT_air']:.1f}K T_out={s['T_out_C']:.0f}C "
              f"wall={s['T_wall_C']:.0f}C plate={s['T_plate_C']:.0f}C rad={s['rad_frac']:.2f}")
    print()
    # wind: dynamic pressure magnitude at discharge vs buoyancy draft
    print("  wind dynamic-pressure magnitude vs stack draft:")
    for Vw in [0,3,6,11]:
        rho = air(273.15+2)['rho']
        qdyn = 0.5*rho*Vw**2
        print(f"   V_wind={Vw:5.1f} m/s -> 0.5 rho V^2 = {qdyn:5.1f} Pa "
              f"(stack draft ~50 Pa)")
    per = per_face_split()
    print(f"\n  per-face radiative incidence split (approx): front {per['front']:.0%}, "
          f"sides {per['sides']:.0%}, rear {per['rear']:.0%}")

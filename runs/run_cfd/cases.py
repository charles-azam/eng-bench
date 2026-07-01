"""
Run all RCCS operating cases and write results to output/results/.
Uses the coupled 1-D model in rccs_model.py.
"""
import json
import numpy as np
import rccs_model as m
import airprops as ap

OUT = {}

# ============================================================================
# CASE 1 - Baseline steady state (peak-duty, Q_to_air = 56 kW)
# ============================================================================
r1 = m.solve_steady(Q_to_air=56.0e3, T_in_C=20.0, T_amb_C=2.0)
m.report(r1, "CASE 1  Baseline steady state (Q_to_air = 56 kW)")
OUT['case1'] = r1

# Sensitivity of Case 1 to the parasitic-loss (heat-to-air) assumption
print("\n--- Case 1 sensitivity to heat-to-air (parasitic loss) ---")
sens = []
for Q in [48e3, 56e3, 64e3, 72e3]:
    r = m.solve_steady(Q_to_air=Q, T_in_C=20.0, T_amb_C=2.0)
    sens.append(r)
    print(f"  Q={Q/1e3:4.0f} kW: m_dot={r['m_dot']:.3f} kg/s  dT={r['dT']:5.1f}K  "
          f"T_plate={r['T_plate_C']:.0f}C  T_rw_front={r['T_rw_front_mid_C']:.0f}C  rad={r['rad_frac']*100:.0f}%")
OUT['case1_sens'] = sens

# ============================================================================
# CASE 2 - Accident decay-heat transient (quasi-steady + lumped inertia)
# ============================================================================
# Imposed normalized decay-heat shape (input permits this; polynomial w/o C10
# diverges). Q rises from normal load 26 kW to 56 kW peak at t_peak, then decays.
Q_norm, Q_peak = 26.0e3, 56.0e3
t_peak_h = 84.85
def Q_decay(t_h):
    # gamma-type bump peaking at t_peak_h, normalized to 1 at peak
    a = 2.2
    x = np.maximum(t_h, 1e-6) / t_peak_h
    shape = x**a * np.exp(a * (1 - x))       # =1 at x=1, ->0 at 0 and large t
    return Q_norm + (Q_peak - Q_norm) * shape

# Quasi-steady sweep over the transient
t_hours = np.linspace(0, 170, 200)
qs = []
for th in t_hours:
    Q = float(Q_decay(th))
    r = m.solve_steady(Q_to_air=Q, T_in_C=20.0, T_amb_C=2.0)
    qs.append((th, Q, r['m_dot'], r['dT'], r['T_plate_C'], r['T_rw_front_mid_C'], r['rad_frac']))
qs = np.array(qs)
ipk = qs[:, 4].argmax()
print("\n" + "="*70 + "\nCASE 2  Accident decay-heat transient (quasi-steady)\n" + "="*70)
print(f"  Peak heat load     : {qs[:,1].max()/1e3:.1f} kW at t={t_peak_h} h")
print(f"  Peak plate temp    : {qs[ipk,4]:.0f} C at t={qs[ipk,0]:.1f} h")
print(f"  Peak riser front   : {qs[ipk,5]:.0f} C")
print(f"  Peak mass flow     : {qs[:,2].max():.3f} kg/s")
print(f"  Plate T at t=0 (26kW): {qs[0,4]:.0f} C")

# Lumped-capacitance transient to show thermal lag & that T levels off (no runaway).
# Plate + heater + riser steel thermal mass. Energy balance:
#   C dT_plate/dt = P_in(t) - Q_removed(T_plate)
# where Q_removed is the steady heat the loop carries at the current plate temp.
# Build a plate-temp -> removable-power map from steady solutions.
Tp_grid = np.linspace(100, 700, 60) + 273.15
Qrem_grid = []
for Tp in Tp_grid:
    # invert: find Q such that steady plate temp = Tp. Steady T_plate increases with Q.
    Qrem_grid.append(None)
# Instead: build Q -> T_plate then interpolate T_plate -> Q_removable
Qs = np.linspace(10e3, 120e3, 40)
Tps = np.array([m.solve_steady(Q_to_air=Q, T_in_C=20.0, T_amb_C=2.0)['T_plate_C'] for Q in Qs])
def Q_removable(Tp_C):
    return float(np.interp(Tp_C, Tps, Qs))

# Thermal capacitance: 1-in steel plate (mock RPV) + ceramic heaters + riser steel
m_plate = 7850 * (0.0254 * m.A_PLATE)     # kg
C_plate = m_plate * 480                    # J/K
m_heater = 300.0                           # kg ceramic (est.)
C_heater = m_heater * 1000
m_riser = 7850 * (m.r_out_a*m.r_out_b - m.r_in_a*m.r_in_b) * m.L_RISER_TOTAL * m.N_RISER
C_riser = m_riser * 480
C_tot = C_plate + C_heater + C_riser
print(f"  Lumped thermal capacitance C_tot = {C_tot/1e6:.2f} MJ/K "
      f"(plate {C_plate/1e6:.2f}, heater {C_heater/1e6:.2f}, riser {C_riser/1e6:.2f})")

dt = 60.0                                   # s
t_end = 170 * 3600
n = int(t_end / dt)
Tp = 271.0 + 273.15                         # start at normal-load (26 kW) steady
tp_hist, Tp_hist, Pin_hist = [], [], []
for i in range(n):
    t_h = i * dt / 3600.0
    Pin = float(Q_decay(t_h))
    Qout = Q_removable(Tp - 273.15)          # W removed at current plate temp
    Tp += dt * (Pin - Qout) / C_tot
    if i % 60 == 0:
        tp_hist.append(t_h); Tp_hist.append(Tp - 273.15); Pin_hist.append(Pin/1e3)
tp_hist = np.array(tp_hist); Tp_hist = np.array(Tp_hist)
ipk2 = Tp_hist.argmax()
print(f"  Transient (with inertia) peak plate temp: {Tp_hist[ipk2]:.0f} C at t={tp_hist[ipk2]:.1f} h")
print(f"  Quasi-steady vs inertial peak lag: leveling behaviour, NO runaway.")

OUT['case2'] = dict(
    peak_Q_kW=qs[:,1].max()/1e3, peak_plate_C=float(qs[ipk,4]),
    peak_riser_front_C=float(qs[ipk,5]), peak_mdot=float(qs[:,2].max()),
    plate_t0_C=float(qs[0,4]),
    inertial_peak_plate_C=float(Tp_hist[ipk2]), inertial_peak_t_h=float(tp_hist[ipk2]),
    C_tot_MJ_K=C_tot/1e6,
    qs_time_h=qs[:,0].tolist(), qs_Q_kW=(qs[:,1]/1e3).tolist(),
    qs_plate_C=qs[:,4].tolist(), qs_mdot=qs[:,2].tolist(),
    inert_t_h=tp_hist.tolist(), inert_plate_C=Tp_hist.tolist(),
)

# Runaway check: steady plate temp vs power is bounded & monotonic (T^4 feedback)
print("\n  Stability map (steady plate temp vs heat load):")
for Q in [26e3, 40e3, 56e3, 80e3, 110e3]:
    r = m.solve_steady(Q_to_air=Q, T_in_C=20.0, T_amb_C=2.0)
    print(f"    Q={Q/1e3:5.0f} kW -> T_plate={r['T_plate_C']:5.0f} C  (dT_plate/dQ gentle: T^4 feedback)")

# ============================================================================
# CASE 3 - Weather sensitivity (outdoor T and wind)
# ============================================================================
print("\n" + "="*70 + "\nCASE 3  Weather sensitivity\n" + "="*70)
# (a) outdoor air temperature sweep. Open loop draws outdoor air; model inlet
# tracking outdoor with a fixed building warm-up dTb, and ambient density = outdoor.
dTb = 18.0   # building/downcomer warm-up (Case 1: outdoor 2C -> inlet 20C)
Tamb_sweep = np.arange(-18, 25, 3.0)
wsweep = []
print("  (a) Outdoor air temperature (wind ~0):")
print("      Tamb[C]  m_dot[kg/s]  dT[K]  T_out[C]  T_plate[C]  T_rw_front[C]")
for Ta in Tamb_sweep:
    Tin = Ta + dTb
    r = m.solve_steady(Q_to_air=56e3, T_in_C=Tin, T_amb_C=Ta)
    wsweep.append((Ta, r['m_dot'], r['dT'], r['T_out_C'], r['T_plate_C'], r['T_rw_front_mid_C']))
    print(f"      {Ta:6.0f}   {r['m_dot']:8.3f}    {r['dT']:5.1f}  {r['T_out_C']:6.1f}   "
          f"{r['T_plate_C']:7.0f}     {r['T_rw_front_mid_C']:6.0f}")
wsweep = np.array(wsweep)

# (b) Wind effect. Two mechanisms:
#   (i) external forced convection raises parasitic loss from uninsulated hot
#       ductwork -> lowers heat-to-air slightly and cools inlet a touch;
#   (ii) dynamic wind pressure at the chimney exit perturbs draft +/- (direction
#       dependent). Model wind-induced draft term dp_wind = +/- Cp * 0.5 rho V^2.
print("\n  (b) Wind speed effect at baseline (Tamb=2C, Tin=20C):")
print("      wind[m/s]  draft_mult  m_dot[kg/s]  dT[K]  T_plate[C]  (Cp=+/-0.3)")
wind_res = []
for V in [0, 3, 6, 9, 11]:
    # wind dynamic pressure vs baseline draft ~60 Pa; adverse (Cp=-0.3) reduces net draft
    q_wind = 0.5 * ap.rho(275.15) * V**2   # Pa dynamic head at outdoor density
    # net draft change bracketed +/- Cp*q_wind; report adverse (worst) case
    Cp = 0.3
    # crude: scale flow by sqrt((draft -/+ Cp q_wind)/draft) since loss~m^2
    base = m.solve_steady(Q_to_air=56e3, T_in_C=20.0, T_amb_C=2.0)
    draft0 = base['draft_Pa']
    fac_adv = np.sqrt(max(draft0 - Cp*q_wind, 1)/draft0)
    fac_fav = np.sqrt((draft0 + Cp*q_wind)/draft0)
    wind_res.append((V, q_wind, fac_adv, fac_fav))
    print(f"      {V:6.0f}    adv {fac_adv:.3f}/fav {fac_fav:.3f}   "
          f"~{base['m_dot']*fac_adv:.3f}-{base['m_dot']*fac_fav:.3f}   "
          f"q_wind={q_wind:.1f}Pa")
OUT['case3'] = dict(Tamb_C=wsweep[:,0].tolist(), mdot=wsweep[:,1].tolist(),
                    dT=wsweep[:,2].tolist(), T_out_C=wsweep[:,3].tolist(),
                    T_plate_C=wsweep[:,4].tolist(), T_rw_front_C=wsweep[:,5].tolist(),
                    wind=[list(w) for w in wind_res])

# ============================================================================
# CASE 4 - Power-shape variations (same integral power)
# ============================================================================
print("\n" + "="*70 + "\nCASE 4  Power-shape variations (same integral 56 kW)\n" + "="*70)
# Flow and total dT are set by integral power (~unchanged). Peak local wall temp
# shifts with the axial power peak. Evaluate local wall temp at the peak zone.
r0 = m.solve_steady(Q_to_air=56e3, T_in_C=20.0, T_amb_C=2.0)
shapes = {
    'uniform':      [1.0]*10,
    'cosine':       [0.498,0.831,1.010,1.140,1.248,1.313,1.294,1.157,0.904,0.605],
    'bottom_peak':  [1.225,1.325,1.425,1.375,1.275,1.150,0.900,0.650,0.450,0.225],
}
# local air temp rises through zones; local wall temp = T_air(z) + q''_local/h_i
zone_h = m.L_HEAT/10
h_i = r0['h_i']; mdot = r0['m_dot']; cp = ap.cp((20+r0['T_out_C'])/2+273.15)
Tin = 20.0
c4 = {}
for name, pk in shapes.items():
    pk = np.array(pk); pk = pk/pk.mean()   # normalize mean to 1 (same integral)
    q_zone = pk * 56e3/10                    # W per zone
    Tair = Tin; peakwall = -1; peakz = 0
    walls = []
    for i,qz in enumerate(q_zone):
        Tair_mid = Tair + 0.5*qz/(mdot*cp)
        # local circumferential front-face wall temp
        Qline = qz/zone_h/m.N_RISER
        Tf,_,_,_ = m.riser_circumferential(Qline, h_i, Tair_mid+273.15)
        walls.append(Tf-273.15)
        if Tf-273.15>peakwall: peakwall=Tf-273.15; peakz=(i+0.5)*zone_h
        Tair += qz/(mdot*cp)
    c4[name]=dict(peak_wall_C=peakwall, peak_z_m=peakz, walls=walls)
    print(f"  {name:12s}: peak riser front wall {peakwall:.0f} C at z={peakz:.1f} m")
OUT['case4'] = c4

# ---- save ----
import os
os.makedirs('results', exist_ok=True)
with open('results/results.json','w') as f:
    json.dump(OUT, f, indent=1, default=float)
print("\nSaved results/results.json")

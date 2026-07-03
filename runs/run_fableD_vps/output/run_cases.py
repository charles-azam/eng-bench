"""Run all operating cases + uncertainty sensitivities. Results -> output/results/."""
import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import rccs_model as m

OUT = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUT, exist_ok=True)

def C(K):
    return K - 273.15

def summarize(st):
    fm = st['flux_mid']
    return dict(
        mdot_kgs=round(st['mdot'], 4), mdot_kgmin=round(st['mdot'] * 60, 1),
        dT_riser=round(st['dT_riser'], 1),
        T_gas_out_C=round(C(st['T_gas_out']), 1),
        T_cav_C=round(C(st['T_cav']), 1),
        T_plate_mid_C=round(C(st['mid']['T_P']), 1),
        T_plate_mean_C=round(C(st['T_plate_mean']), 1),
        T_plate_max_C=round(C(st['T_plate_max']), 1),
        T_duct_front_mid_C=round(C(st['mid']['T_F']), 1),
        T_duct_side_mid_C=round(C(st['mid']['T_S']), 1),
        T_duct_rear_mid_C=round(C(st['mid']['T_R']), 1),
        T_heater_mean_C=round(C(np.mean([r['T_h'] for r in st['rows']])), 1),
        Q_gas_kW=round(st['Q_gas'] / 1e3, 2),
        Q_rad_ducts_kW=round(st['Q_rad_ducts'] / 1e3, 2),
        Q_conv_ducts_kW=round(st['Q_conv_ducts'] / 1e3, 2),
        rad_fraction=round(st['rad_fraction'], 3),
        Q_parasitic_kW=round((st['P_elec'] - st['Q_gas']) / 1e3, 2),
        flux_front_mid=round(fm['front']['rad'] + fm['front']['conv'], 0),
        flux_front_rad=round(fm['front']['rad'], 0),
        dp_buoy_Pa=round(st['dp']['dp_buoy'], 1),
    )

results = {}

# --------------------------------------------------------------- Case 1 baseline
print("Case 1 baseline ...")
base = m.steady_solve(P_elec=82e3, T_out=275.15, T_bldg=293.15, wind=0.0)
results['case1_baseline'] = summarize(base)
print(m.report(base, "Case 1"))

# axial profiles for the note
prof = dict(z=[r['z'] for r in base['rows']],
            T_plate=[C(r['T_P']) for r in base['rows']],
            T_front=[C(r['T_F']) for r in base['rows']],
            T_side=[C(r['T_S']) for r in base['rows']],
            T_gas=[C(0.5 * (r['T_gas_in'] + r['T_gas_out'])) for r in base['rows']])
results['case1_profiles'] = prof

# --------------------------------------------------------------- sensitivities
print("sensitivities ...")
sens = {}
variations = [
    ('eps_duct', [0.70, 0.80, 0.90]),
    ('eps_plate', [0.70, 0.785, 0.90]),
    ('f_edge_loss', [0.02, 0.05, 0.10]),
    ('K_conditioner', [0.5, 2.0, 4.0]),
    ('K_dampers', [0.5, 1.0, 2.5]),
    ('rough', [5e-5, 1.5e-4, 4.5e-4]),
]
for name, vals in variations:
    sens[name] = []
    for v in vals:
        st = m.steady_solve(prm={name: v})
        s = summarize(st)
        s[name] = v
        sens[name].append(s)
        print(f"  {name}={v}: mdot {s['mdot_kgs']}, dT {s['dT_riser']}, "
              f"plate {s['T_plate_mean_C']}, radfrac {s['rad_fraction']}")
# geometry/assumption extras: intake elevation
sens['z_intake'] = []
for zi in [0.5, 3.5, 7.0]:
    old = m.GEO['z_intake']
    m.GEO['z_intake'] = zi
    st = m.steady_solve()
    s = summarize(st)
    s['z_intake'] = zi
    sens['z_intake'].append(s)
    m.GEO['z_intake'] = old
results['sensitivity'] = sens

# --------------------------------------------------------------- Case 2 transient
print("Case 2 transient ...")

def P_decay(t_h):
    """Scaled decay-heat electric power [W]. Shape imposed per inputs' fallback:
    26.16 kW normal load rising to 56.07 kW at 84.85 h, then slow decay-heat-like
    decline ~ t^-0.28. (The 10th-order polynomial in the source is unusable as
    given: its C10 term is missing and it diverges after ~110 h.)"""
    P0, Ppk, tpk = 26.16e3, 56.07e3, 84.85
    if t_h <= 0:
        return P0
    if t_h <= tpk:
        return P0 + (Ppk - P0) * np.sin(0.5 * np.pi * t_h / tpk) ** 1.5
    return Ppk * (t_h / tpk) ** -0.28

# quasi-steady cavity heat removal vs (uniform) plate temperature, precomputed
print("  building Q_cav(T_plate) table ...")
Tp_grid = np.array([340, 380, 420, 460, 500, 540, 580, 620, 660, 700, 740.])
Qcav_grid, mdot_grid, Tout_grid, Tfront_grid = [], [], [], []
for Tp in Tp_grid:
    st = m.steady_solve(P_elec=0.0, T_plate_fixed=np.full(m.NSEG, Tp),
                        mdot_bracket=(0.02, 4.0))
    # heat leaving the plate front = what the loop removes + cavity wall losses
    Qcav = st['Q_gas'] + st['Q_rearwall'] + st['Q_sidewall']
    Qcav_grid.append(Qcav)
    mdot_grid.append(st['mdot'])
    Tout_grid.append(st['T_gas_out'])
    Tfront_grid.append(st['mid']['T_F'])
    print(f"    Tp={Tp-273.15:.0f}C -> Qcav {Qcav/1e3:.1f} kW, mdot {st['mdot']:.3f}")
Qcav_grid = np.array(Qcav_grid)

def Q_cav(Tp):
    return np.interp(Tp, Tp_grid, Qcav_grid)

# two-node ODE: heater array (C_h) radiating to plate back; plate (C_p) to cavity
C_p = m.GEO['A_plate'] * m.GEO['t_plate'] * 7850 * 480          # ~975 kJ/K
C_h = 400e3    # ASSUMED heater+backing+board thermal mass, J/K (sensitivity below)
Rr = 1 / m.PARAMS['eps_heater'] + 1 / m.PARAMS['eps_plate_back'] - 1
A_p = m.GEO['A_plate']

def q_h2p(Th, Tp):
    return A_p * m.SIGMA * (Th ** 4 - Tp ** 4) / Rr

def q_back(Th, T_bldg=293.15):
    R = m.GEO['t_dur'] / m.k_duraboard(Th) + m.PARAMS['R_ext']
    return A_p * (Th - T_bldg) / R

def transient(C_h_val, f_edge=0.05, t_end=170.0, dt_h=0.02):
    n = int(t_end / dt_h)
    t = np.linspace(0, t_end, n)
    Th = np.zeros(n)
    Tp = np.zeros(n)
    # initial steady state at P(0)
    from scipy.optimize import fsolve
    def ss(x):
        return [P_decay(0) * (1 - f_edge) - q_h2p(x[0], x[1]) - q_back(x[0]),
                q_h2p(x[0], x[1]) - Q_cav(x[1])]
    x0 = fsolve(ss, [650.0, 550.0])
    Th[0], Tp[0] = x0
    dt = dt_h * 3600
    for i in range(1, n):
        P = P_decay(t[i - 1]) * (1 - f_edge)
        qhp = q_h2p(Th[i - 1], Tp[i - 1])
        Th[i] = Th[i - 1] + dt / C_h_val * (P - qhp - q_back(Th[i - 1]))
        Tp[i] = Tp[i - 1] + dt / C_p * (qhp - Q_cav(Tp[i - 1]))
    return t, Th, Tp

t, Th, Tp = transient(C_h)
mdot_t = np.interp(Tp, Tp_grid, mdot_grid)
Tout_t = np.interp(Tp, Tp_grid, Tout_grid)
Tfront_t = np.interp(Tp, Tp_grid, Tfront_grid)
ipk = int(np.argmax(Tp))
results['case2'] = dict(
    T_plate_peak_C=round(C(Tp[ipk]), 1),
    t_peak_h=round(t[ipk], 1),
    T_heater_peak_C=round(C(Th.max()), 1),
    mdot_peak_kgs=round(float(mdot_t.max()), 3),
    dT_riser_peak=round(float(Tout_t.max() - 293.15), 1),
    T_duct_front_peak_C=round(C(float(Tfront_t.max())), 1),
    T_plate_initial_C=round(C(Tp[0]), 1),
    levels_off=bool(Tp[ipk] < Tp[-1] + 1e9 and ipk < len(t) - 5),
)
# thermal-mass sensitivity (does C_h matter? quasi-steady check)
for Ch2 in [200e3, 800e3]:
    t2, Th2, Tp2 = transient(Ch2)
    results['case2'][f'T_plate_peak_C_Ch{int(Ch2/1e3)}k'] = round(C(Tp2.max()), 1)
print(f"  peak plate {results['case2']['T_plate_peak_C']} C at "
      f"{results['case2']['t_peak_h']} h; peak mdot {results['case2']['mdot_peak_kgs']}")

fig, ax = plt.subplots(2, 1, figsize=(8, 8), sharex=True)
ax[0].plot(t, [P_decay(x) / 1e3 for x in t], label='electric power [kW]')
ax[0].set_ylabel('kW')
ax[0].legend()
ax[0].grid(alpha=.3)
ax[1].plot(t, Tp - 273.15, label='plate')
ax[1].plot(t, Th - 273.15, label='heater array')
ax[1].plot(t, Tfront_t - 273.15, label='duct front (mid)')
ax[1].axhline(538, color='r', ls='--', label='538 C accident limit')
ax[1].set_xlabel('time [h]')
ax[1].set_ylabel('deg C')
ax[1].legend()
ax[1].grid(alpha=.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'case2_transient.png'), dpi=130)
np.savetxt(os.path.join(OUT, 'case2_transient.csv'),
           np.column_stack([t, Tp - 273.15, Th - 273.15, mdot_t, Tout_t - 273.15]),
           delimiter=',', header='t_h,T_plate_C,T_heater_C,mdot_kgs,T_gas_out_C',
           comments='')

# --------------------------------------------------------------- Case 3 weather
print("Case 3 weather ...")
weather = []
for Tout_C in [-18, -10, 0, 2, 10, 24]:
    st = m.steady_solve(T_out=Tout_C + 273.15)
    s = summarize(st)
    s['T_out_C'] = Tout_C
    s['wind'] = 0.0
    s['Cp'] = 0.0
    weather.append(s)
    print(f"  T_out={Tout_C:+d}C: mdot {s['mdot_kgs']}, dT {s['dT_riser']}, "
          f"plate {s['T_plate_mean_C']}")
for wind in [2, 5, 8, 11]:
    for Cp in [-0.5, -0.25, 0.2]:
        st = m.steady_solve(T_out=275.15, wind=wind, prm={'Cp_wind': Cp})
        s = summarize(st)
        s['T_out_C'] = 2
        s['wind'] = wind
        s['Cp'] = Cp
        weather.append(s)
        print(f"  wind={wind} m/s Cp={Cp}: mdot {s['mdot_kgs']}, "
              f"plate {s['T_plate_mean_C']}")
results['case3_weather'] = weather

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
w0 = [w for w in weather if w['wind'] == 0]
ax[0].plot([w['T_out_C'] for w in w0], [w['mdot_kgs'] for w in w0], 'o-')
ax[0].set_xlabel('outdoor T [C]')
ax[0].set_ylabel('mass flow [kg/s]')
ax[0].grid(alpha=.3)
ax[0].set_title('no wind')
for Cp, mk in [(-0.5, 'o-'), (-0.25, 's-'), (0.2, '^-')]:
    ws = [w for w in weather if w['Cp'] == Cp and w['wind'] > 0]
    ax[1].plot([0] + [w['wind'] for w in ws],
               [w0[3]['mdot_kgs']] + [w['mdot_kgs'] for w in ws], mk,
               label=f'Cp={Cp}')
ax[1].set_xlabel('wind speed [m/s]')
ax[1].set_ylabel('mass flow [kg/s]')
ax[1].grid(alpha=.3)
ax[1].legend()
ax[1].set_title('outdoor +2 C')
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'case3_weather.png'), dpi=130)

# --------------------------------------------------------------- Case 4 power shapes
print("Case 4 power shapes ...")
shapes = dict(
    cosine=[0.498, 0.831, 1.010, 1.140, 1.248, 1.313, 1.294, 1.157, 0.904, 0.605],
    bottom=[1.225, 1.325, 1.425, 1.375, 1.275, 1.150, 0.900, 0.650, 0.450, 0.225],
)
case4 = {}
for nm, sh in shapes.items():
    st = m.steady_solve(shape=sh)
    s = summarize(st)
    case4[nm] = s
    print(f"  {nm}: mdot {s['mdot_kgs']}, dT {s['dT_riser']}, "
          f"plate max {s['T_plate_max_C']}")
results['case4'] = case4

with open(os.path.join(OUT, 'results.json'), 'w') as f:
    json.dump(results, f, indent=1)
print("done -> results/results.json")

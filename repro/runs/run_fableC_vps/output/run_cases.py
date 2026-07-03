"""Run all operating cases and dump results to JSON/CSV for the calc note."""
import json
import numpy as np
import rccs_model as M
import airprops as air

C0 = 273.15
OUT = {}


def strip(o):
    """drop the profile list, keep scalars"""
    d = {k: v for k, v in o.items() if k != "prof"}
    d["profile"] = [
        {k: p[k] for k in ("z", "Tp", "Tf", "Ts", "Tr", "Tw", "Tair",
                           "h_i", "Re")}
        for p in o["prof"]]
    return d


# ---------------------------------------------------------------- Case 1
print("== Case 1: baseline 82 kWe ==", flush=True)
c1 = M.solve_steady(P_elec=82e3, T_outdoor=2 + C0, T_bldg=20 + C0,
                    verbose=True)
OUT["case1"] = strip(c1)

print("\n== Normal-operation duty 26.16 kWe ==", flush=True)
cn = M.solve_steady(P_elec=26.16e3, T_outdoor=2 + C0, T_bldg=20 + C0,
                    verbose=True)
OUT["normal_op"] = strip(cn)

print("\n== Steady at accident peak power 56.07 kWe ==", flush=True)
cp = M.solve_steady(P_elec=56.07e3, T_outdoor=2 + C0, T_bldg=20 + C0,
                    verbose=True)
OUT["peak_steady"] = strip(cp)

# ------------------------------------------------------- Case 1 sensitivity
print("\n== Sensitivities on Case 1 ==", flush=True)
sens = {}

def run_sens(tag, setup, teardown):
    setup()
    try:
        o = M.solve_steady(P_elec=82e3, T_outdoor=2 + C0, T_bldg=20 + C0)
        sens[tag] = dict(m_dot=o["m_dot"], dT=o["dT"], Tp_mid=o["Tp_mid"],
                         Tf_mid=o["Tf_mid"],
                         frad=o["Q_rad_risers"] / (o["Q_rad_risers"]
                                                   + o["Q_conv_risers"]))
        print(f"{tag:28s} m={o['m_dot']:.3f} dT={o['dT']:.1f} "
              f"Tp={o['Tp_mid']-C0:.0f}C Tf={o['Tf_mid']-C0:.0f}C",
              flush=True)
    finally:
        teardown()

eps0 = M.EPS_VEC.copy()
for e in (0.70, 0.90):
    run_sens(f"riser eps={e}",
             lambda e=e: M.EPS_VEC.__setitem__(slice(1, 4), e),
             lambda: M.EPS_VEC.__setitem__(slice(0, 5), eps0))
for fs in (0.5, 1.5):
    def setup(fs=fs):
        M.FORM_SCALE = fs
    def teardown():
        M.FORM_SCALE = 1.0
    run_sens(f"form losses x{fs}", setup, teardown)
# plate emissivity range 0.7 / 0.9
for e in (0.70, 0.90):
    run_sens(f"plate eps={e}",
             lambda e=e: M.EPS_VEC.__setitem__(0, e),
             lambda: M.EPS_VEC.__setitem__(0, eps0[0]))
# chimney heat loss doubled
ua0 = M.UA_CHIM_PER_M
def s_ua():
    M.UA_CHIM_PER_M = 2 * ua0
def t_ua():
    M.UA_CHIM_PER_M = ua0
run_sens("chimney UA x2", s_ua, t_ua)
# downcomer inlet elevation
z0 = M.Z_DC_IN
for z in (1.5, 8.0):
    def s_z(z=z):
        M.Z_DC_IN = z
    def t_z():
        M.Z_DC_IN = z0
    run_sens(f"downcomer inlet z={z} m", s_z, t_z)
OUT["sensitivity"] = sens

# ---------------------------------------------------------------- Case 2
print("\n== Case 2: decay-heat transient ==", flush=True)
TP_GRID = np.array([360, 400, 450, 500, 550, 600, 650, 700, 750, 800,
                    900, 1000.0])
qrem, mflow, qback, dts = [], [], [], []
for Tp in TP_GRID:
    o = M.solve_steady(T_plate_fixed=Tp, T_outdoor=2 + C0, T_bldg=20 + C0)
    # heater-back loss with heater sheet ~ plate temperature
    R_back = M.TH_DUR / M.k_duraboard((Tp + 293.15) / 2) + 1 / M.H_OUT
    qb = M.A_PLATE * (Tp - 293.15) / R_back
    qrem.append(o["Q_plate_total"])
    mflow.append(o["m_dot"])
    qback.append(qb)
    dts.append(o["dT"])
    print(f"Tp={Tp-C0:5.0f}C  Q_removed={o['Q_plate_total']/1e3:6.1f} kW  "
          f"m={o['m_dot']:.3f} kg/s  dT={o['dT']:.1f} K", flush=True)
qrem, mflow, qback, dts = map(np.array, (qrem, mflow, qback, dts))
OUT["char_curve"] = dict(Tp=TP_GRID.tolist(), Q_removed=qrem.tolist(),
                         m_dot=mflow.tolist(), Q_back=qback.tolist(),
                         dT=dts.tolist())

TP_PEAK = 84.85  # h


def P_decay(t_h):
    """imposed decay-power shape: 26.16 -> 56.07 kW peak at 84.85 h, then
    slow decay-heat-like decline ~ t^-0.25 (assumed; results quasi-steady)."""
    if t_h <= TP_PEAK:
        return 26.16e3 + (56.07e3 - 26.16e3) * np.sin(
            0.5 * np.pi * t_h / TP_PEAK) ** 2
    return 56.07e3 * (t_h / TP_PEAK) ** -0.25


C_EFF = 1.25e6   # J/K: plate steel 0.87 MJ/K + heaters/board/frame ~0.4

T0 = float(np.interp(26.16e3, qrem + qback, TP_GRID))
t_end = 250.0
dt = 0.05
ts, Tps = [0.0], [T0]
t, Tp = 0.0, T0
while t < t_end:
    P = P_decay(t)
    Qr = np.interp(Tp, TP_GRID, qrem)
    Qb = np.interp(Tp, TP_GRID, qback)
    Tp += dt * 3600 * (P - Qr - Qb) / C_EFF
    t += dt
    ts.append(t)
    Tps.append(Tp)
ts = np.array(ts)
Tps = np.array(Tps)
ipk = Tps.argmax()
m_t = np.interp(Tps, TP_GRID, mflow)
dT_t = np.interp(Tps, TP_GRID, dts)
print(f"peak plate T = {Tps[ipk]-C0:.0f} C at t = {ts[ipk]:.1f} h "
      f"(power peak {TP_PEAK} h)")
print(f"peak mass flow = {m_t.max():.3f} kg/s; peak riser dT = "
      f"{dT_t.max():.1f} K")
OUT["case2"] = dict(
    t_h=ts[::20].tolist(), Tp=Tps[::20].tolist(),
    m_dot=m_t[::20].tolist(), dT=dT_t[::20].tolist(),
    P_kW=[P_decay(x) / 1e3 for x in ts[::20]],
    T0=T0, C_eff=C_EFF, Tp_peak=float(Tps[ipk]), t_peak=float(ts[ipk]),
    m_peak=float(m_t.max()), dT_peak=float(dT_t.max()))

# ---------------------------------------------------------------- Case 3
print("\n== Case 3: weather sensitivity ==", flush=True)
sweep = []
for Tout in (-18, -10, -2, 6, 14, 24):
    for mode in ("building_inlet", "outdoor_inlet"):
        Tin = 20 + C0 if mode == "building_inlet" else Tout + C0
        o = M.solve_steady(P_elec=82e3, T_outdoor=Tout + C0,
                           T_bldg=20 + C0, T_inlet=Tin)
        sweep.append(dict(T_out=Tout, mode=mode, m_dot=o["m_dot"],
                          dT=o["dT"], Tp_mid=o["Tp_mid"] - C0,
                          Tf_mid=o["Tf_mid"] - C0,
                          T_exit=o["T_out"] - C0))
        print(f"Tout={Tout:+3d}C {mode:15s} m={o['m_dot']:.3f} "
              f"dT={o['dT']:.1f} Tp={o['Tp_mid']-C0:.0f}C", flush=True)
OUT["weather_T"] = sweep

windrows = []
for wind in (0, 2, 5, 8, 11):
    for cpw, tag in ((0.3, "adverse"), (-0.3, "favorable")):
        o = M.solve_steady(P_elec=82e3, T_outdoor=2 + C0, T_bldg=20 + C0,
                           wind=wind, cp_wind=cpw)
        windrows.append(dict(wind=wind, cp=cpw, tag=tag, m_dot=o["m_dot"],
                             dT=o["dT"], Tp_mid=o["Tp_mid"] - C0))
        print(f"wind={wind:4.1f} m/s {tag:9s} m={o['m_dot']:.3f} "
              f"dT={o['dT']:.1f} Tp={o['Tp_mid']-C0:.0f}C", flush=True)
OUT["weather_wind"] = windrows

with open("results.json", "w") as f:
    json.dump(OUT, f, indent=1)
print("\nresults.json written")

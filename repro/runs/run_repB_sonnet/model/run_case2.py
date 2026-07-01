"""
Case 2 -- accident decay-heat transient (quasi-steady approximation).

Justification for quasi-steady treatment: the plate/riser thermal diffusion
time constant is ~ (thickness)^2/alpha. For the 25.4mm SAE1020 plate,
alpha = k/(rho*cp) = 50/(7850*480) = 1.33e-5 m^2/s, tau ~ (0.0254)^2/1.33e-5
~ 48 s. Riser wall (4.775mm) is even faster. Bulk-air transport time around
the ~30 m loop at ~1-5 m/s is ~ 10-30 s. All of these are 3-4 orders of
magnitude shorter than the ~hours timescale over which the decay-heat curve
changes (dP/dt ~ kWt/hour) -> the loop re-equilibrates essentially
instantaneously relative to the power ramp, so at each instant t the system
is well approximated by the STEADY-STATE solution for Q(t). This is a
standard simplification for slow transients (quasi-steady-state approach).
"""
import json
import numpy as np
import loop_solver as L
from decay_heat_curve import decay_heat_kWt, T_PEAK_H, P0_KWT, PPEAK_KWT

T_AMB = 2.0 + 273.15
T_INLET = 20.0 + 273.15

t_hours = np.concatenate([np.linspace(0, 40, 9), np.linspace(40, 130, 19),
                           np.linspace(130, 400, 12)])
t_hours = np.unique(np.round(t_hours, 3))

rows = []
for th in t_hours:
    Qk = float(decay_heat_kWt(th))
    res = L.solve_case(Qk * 1000.0, T_AMB, T_INLET, wind_speed=0.5, N=30)
    rr = res["riser"]
    z_mm = rr["z"] * 1000
    i_mid = np.argmin(np.abs(z_mm - 3500))
    rows.append(dict(t_h=th, Q_kWt=Qk, m_dot_kg_s=res["m_dot"],
                      T_out_C=rr["T_air"][-1] - 273.15,
                      T_plate_mid_C=rr["T_plate"][i_mid] - 273.15,
                      T_plate_max_C=rr["T_plate"].max() - 273.15,
                      T_F_mid_C=rr["T_F"][i_mid] - 273.15,
                      T_F_max_C=rr["T_F"].max() - 273.15,
                      rad_frac=rr["Q_rad_total"] / (rr["Q_rad_total"] + rr["Q_conv_total"])))

i_peak = int(np.argmax([r["T_plate_max_C"] for r in rows]))
peak = rows[i_peak]

# extra: check for thermal runaway by sweeping power well beyond the stated
# accident peak, to see whether a steady solution keeps existing (i.e. the
# passive system's removal capacity keeps pace with power, or not).
Q_sweep_kWt = np.array([20, 40, 56.07, 80, 100, 130, 160, 200, 250])
runaway_check = []
for Qk in Q_sweep_kWt:
    res = L.solve_case(float(Qk) * 1000.0, T_AMB, T_INLET, wind_speed=0.5, N=25)
    rr = res["riser"]
    runaway_check.append(dict(Q_kWt=float(Qk), m_dot_kg_s=res["m_dot"],
                               T_plate_max_C=rr["T_plate"].max() - 273.15))

out = {
    "case": "Case 2 - accident decay-heat transient (quasi-steady)",
    "note_on_power_curve": "Polynomial C0-C9 does not reproduce the stated "
        "control points (see decay_heat_curve.py); used the input file's own "
        "fallback -- a smooth curve through (26.16 kWt @ t=0, 56.07 kWt @ "
        "t=84.85h peak, exponential decay tau=200h assumed after peak).",
    "transient_table": rows,
    "peak": dict(t_h=peak["t_h"], Q_kWt=peak["Q_kWt"],
                 T_plate_max_C=peak["T_plate_max_C"],
                 T_F_max_C=peak["T_F_max_C"],
                 m_dot_kg_s=peak["m_dot_kg_s"]),
    "runaway_check_vs_power": runaway_check,
    "quasi_steady_justification": {
        "plate_thermal_time_constant_s": 48,
        "loop_transport_time_s": "10-30",
        "power_ramp_timescale_h": "~85",
    },
}

print(json.dumps(out, indent=2))
with open("../results/case2_transient.json", "w") as f:
    json.dump(out, f, indent=2)

"""
Case 3 -- weather sensitivity. Same baseline heat load (82 kWe, Case 1) with
outdoor air temperature swept -18..+24 C and wind speed 0..~11 m/s.

Assumption: the facility/cavity is INDOORS (Case 1 distinguishes "outdoor air"
from "building/inlet air"); we hold the building/inlet air fixed at 20 C
across this sweep (a climate-controlled test building does not track outdoor
swings 1:1) and vary only the OUTDOOR air temperature, which sets (a) the
reference/displaced-column density in the buoyancy balance and (b) the
chimney-discharge ambient point. This reproduces the Case-1 structure (T_amb
!= T_inlet) rather than assuming direct outdoor-air intake.
"""
import json
import numpy as np
import loop_solver as L

Q_ELECTRIC = 82000.0
T_INLET = 20.0 + 273.15

T_amb_C_list = np.array([-18, -10, -2, 2, 10, 18, 24])
wind_list = np.array([0, 2, 5, 8, 11])

rows = []
for Tc in T_amb_C_list:
    for V in wind_list:
        res = L.solve_case(Q_ELECTRIC, Tc + 273.15, T_INLET, wind_speed=float(V), N=30)
        rr = res["riser"]
        z_mm = rr["z"] * 1000
        i_mid = np.argmin(np.abs(z_mm - 3500))
        rows.append(dict(T_amb_C=float(Tc), wind_m_s=float(V),
                          m_dot_kg_s=res["m_dot"],
                          riser_dT_C=rr["T_air"][-1] - rr["T_air"][0],
                          T_plate_mid_C=rr["T_plate"][i_mid] - 273.15,
                          T_F_mid_C=rr["T_F"][i_mid] - 273.15))

# reference (baseline case-1-like point: T_amb=2C, wind~0.5)
ref = L.solve_case(Q_ELECTRIC, 2 + 273.15, T_INLET, wind_speed=0.0, N=30)
ref_mdot = ref["m_dot"]

# wind-direction sensitivity band (Cp uncertain sign/magnitude, see loop_solver.wind_stack_pressure)
Cp_rows = []
for Cp in [-0.8, -0.4, 0.0, 0.3]:
    for V in [0, 5, 11]:
        res = L.solve_case(Q_ELECTRIC, 2 + 273.15, T_INLET, wind_speed=float(V), Cp_wind=Cp, N=25)
        Cp_rows.append(dict(Cp=Cp, wind_m_s=V, m_dot_kg_s=res["m_dot"]))

out = {
    "case": "Case 3 - weather sensitivity",
    "assumption": "Building/inlet air held fixed at 20C; outdoor air temperature "
                   "(sets buoyancy reference column + chimney discharge ambient) "
                   "swept -18..24C. Wind enters via a stack-suction pressure term "
                   "at the chimney discharge (Cp_wind, default -0.4, aiding).",
    "reference_point_Tamb2C_wind0": {"m_dot_kg_s": ref_mdot},
    "sweep": rows,
    "wind_Cp_sensitivity_band": Cp_rows,
}
print(json.dumps(out, indent=2))
with open("../results/case3_weather.json", "w") as f:
    json.dump(out, f, indent=2)

# quick summary printed to stdout
print("\n--- summary: m_dot vs T_amb (wind=0) ---")
for r in rows:
    if r["wind_m_s"] == 0.0:
        print(f"T_amb={r['T_amb_C']:6.1f}C  m_dot={r['m_dot_kg_s']:.4f} kg/s  "
              f"dT={r['riser_dT_C']:.1f}C  T_plate_mid={r['T_plate_mid_C']:.1f}C")

print("\n--- summary: m_dot vs wind (T_amb=2C) ---")
for r in rows:
    if r["T_amb_C"] == 2.0:
        print(f"wind={r['wind_m_s']:5.1f}m/s  m_dot={r['m_dot_kg_s']:.4f} kg/s  "
              f"dT={r['riser_dT_C']:.1f}C")

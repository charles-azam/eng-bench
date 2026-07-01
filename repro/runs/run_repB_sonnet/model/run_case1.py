"""Case 1 -- baseline steady state. 82 kWe, outdoor +2C, building/inlet air 20C,
low wind. Reports mass flow, riser dT, wall/plate temps (at Riser-7 midplane,
z=3500mm, matching the instrumentation map), and the radiation/convection split.
"""
import json
import numpy as np
import geometry as G
import loop_solver as L

T_AMB = 2.0 + 273.15
T_INLET = 20.0 + 273.15
Q_ELECTRIC = 82000.0

res = L.solve_case(Q_ELECTRIC, T_AMB, T_INLET, wind_speed=0.5, N=60)

rr = res["riser"]
z_mm = rr["z"] * 1000
i_mid = np.argmin(np.abs(z_mm - 3500))

rad_frac = rr["Q_rad_total"] / (rr["Q_rad_total"] + rr["Q_conv_total"])

out = {
    "case": "Case 1 - baseline steady state",
    "inputs": {"Q_electric_W": Q_ELECTRIC, "T_ambient_C": T_AMB - 273.15,
               "T_inlet_C": T_INLET - 273.15, "wind_m_s": 0.5},
    "mass_flow_kg_s": res["m_dot"],
    "mass_flow_kg_min": res["m_dot"] * 60,
    "T_air_inlet_C": rr["T_air"][0] - 273.15,
    "T_air_outlet_C": rr["T_air"][-1] - 273.15,
    "riser_deltaT_C": rr["T_air"][-1] - rr["T_air"][0],
    "T_out_chimney_C": res["T_out_chimney"] - 273.15,
    "at_z3500mm": {
        "T_plate_front_C": rr["T_plate"][i_mid] - 273.15,
        "T_riser_hotface_front_C": rr["T_F"][i_mid] - 273.15,
        "T_riser_side_C": rr["T_S"][i_mid] - 273.15,
        "T_riser_rear_C": rr["T_R"][i_mid] - 273.15,
    },
    "plate_temp_range_C": [rr["T_plate"].min() - 273.15, rr["T_plate"].max() - 273.15],
    "riser_hotface_temp_range_C": [rr["T_F"].min() - 273.15, rr["T_F"].max() - 273.15],
    "heat_split": {
        "Q_radiative_kW": rr["Q_rad_total"] / 1000,
        "Q_convective_cavity_kW": rr["Q_conv_total"] / 1000,
        "radiative_fraction": rad_frac,
    },
    "parasitic_loss": {
        "fraction_of_electric_power": res["f_loss"],
        "Q_duraboard_backside_kW": res["Q_dura"] / 1000,
        "Q_superisol_sidewalls_kW": res["Q_super"] / 1000,
        "Q_net_to_cavity_kW": res["Q_net"] / 1000,
    },
    "momentum_balance_Pa": {
        "buoyancy": res["dp_buoy"], "wind_assist": res["dp_wind"],
        "friction_total": res["dp_fric"], "friction_breakdown": res["dp_details"],
    },
    "Reynolds_number_range": [float(rr["Re"].min()), float(rr["Re"].max())],
}

print(json.dumps(out, indent=2))
with open("../results/case1_baseline.json", "w") as f:
    json.dump(out, f, indent=2)

# ---- also dump full axial profile for plotting ----
np.savez("../results/case1_profile.npz", z=rr["z"], T_air=rr["T_air"],
         T_plate=rr["T_plate"], T_F=rr["T_F"], T_S=rr["T_S"], T_R=rr["T_R"],
         Re=rr["Re"], q_rad=rr["q_rad"], q_conv_cav=rr["q_conv_cav"])

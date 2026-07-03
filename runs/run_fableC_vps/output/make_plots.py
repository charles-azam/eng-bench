"""Figures for the calculation note (reads results.json)."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

C0 = 273.15
with open("results.json") as f:
    R = json.load(f)

plt.rcParams.update({
    "figure.dpi": 150, "font.size": 9.5, "axes.grid": True,
    "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 1.8,
})
BLUE, ORANGE, GREEN, RED, GRAY = ("#3B6FB6", "#E08A2E", "#4E9A6C",
                                  "#C24E4E", "#666666")

# ---------------------------------------------------------- axial profiles
p = R["case1"]["profile"]
z = [q["z"] for q in p]
fig, ax = plt.subplots(figsize=(6.2, 4.2))
ax.plot([q["Tp"] - C0 for q in p], z, color=RED, label="heated plate")
ax.plot([q["Tf"] - C0 for q in p], z, color=ORANGE, label="riser front face")
ax.plot([q["Ts"] - C0 for q in p], z, color=GREEN, label="riser side face")
ax.plot([q["Tair"] - C0 for q in p], z, color=BLUE, label="riser air (bulk)")
ax.axhline(3.5, color=GRAY, lw=0.8, ls="--")
ax.text(30, 3.55, "instrument mid-plane z = 3.5 m", color=GRAY, fontsize=8)
ax.set_xlabel("temperature (°C)")
ax.set_ylabel("height above heated-section bottom, z (m)")
ax.set_title("Case 1 (82 kWe): axial temperature profiles")
ax.legend(frameon=False, loc="lower right")
fig.tight_layout()
fig.savefig("fig1_axial_profiles.png")

# ------------------------------------------------- removal characteristic
cc = R["char_curve"]
Tp = np.array(cc["Tp"]) - C0
Qtot = (np.array(cc["Q_removed"]) + np.array(cc["Q_back"])) / 1e3
fig, ax = plt.subplots(figsize=(6.2, 4.2))
ax.plot(Tp, Qtot, color=BLUE, label="heat removal (RCCS + parasitic)")
for P, tag in ((26.16, "normal duty 26.16 kW"),
               (56.07, "accident peak 56.07 kW")):
    ax.axhline(P, color=GRAY, lw=0.9, ls="--")
    Teq = np.interp(P, Qtot, Tp)
    ax.plot([Teq], [P], "o", color=RED, ms=5)
    ax.annotate(f"{tag}\nequilibrium ≈ {Teq:.0f} °C",
                (Teq, P), textcoords="offset points", xytext=(8, -26),
                fontsize=8)
ax.set_xlabel("plate (mock-vessel) temperature (°C)")
ax.set_ylabel("removed power (kW)")
ax.set_title("Passive heat-removal characteristic — monotonic ⇒ no runaway")
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig("fig2_removal_characteristic.png")

# ------------------------------------------------------------- transient
c2 = R["case2"]
t = np.array(c2["t_h"])
fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.4, 5.4), sharex=True)
a1.plot(t, c2["P_kW"], color=GRAY, label="imposed decay power (kW)")
a1.plot(t, (np.array(c2["Tp"]) - C0) / 10, color=RED,
        label="plate temperature (°C ÷ 10)")
a1.axvline(c2["t_peak"], color=RED, lw=0.8, ls=":")
a1.annotate(f"peak {c2['Tp_peak']-C0:.0f} °C @ {c2['t_peak']:.0f} h",
            (c2["t_peak"], (c2["Tp_peak"] - C0) / 10),
            textcoords="offset points", xytext=(6, 6), fontsize=8, color=RED)
a1.set_ylabel("power / scaled temperature")
a1.legend(frameon=False)
a1.set_title("Case 2: decay-heat transient (½-scale)")
a2.plot(t, c2["m_dot"], color=BLUE, label="loop mass flow (kg/s)")
a2b = a2.twinx()
a2b.plot(t, c2["dT"], color=ORANGE, label="riser ΔT (K)")
a2b.set_ylabel("riser ΔT (K)", color=ORANGE)
a2b.grid(False)
a2.set_ylabel("mass flow (kg/s)", color=BLUE)
a2.set_xlabel("time (h)")
fig.tight_layout()
fig.savefig("fig3_transient.png")

# ------------------------------------------------------------- weather
wt = R["weather_T"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.6, 3.8))
for mode, col, lab in (("building_inlet", BLUE, "inlet air 20 °C (building)"),
                       ("outdoor_inlet", ORANGE, "inlet air = outdoor")):
    rows = [r for r in wt if r["mode"] == mode]
    a1.plot([r["T_out"] for r in rows], [r["m_dot"] for r in rows],
            "-o", ms=4, color=col, label=lab)
    a2.plot([r["T_out"] for r in rows], [r["Tp_mid"] for r in rows],
            "-o", ms=4, color=col, label=lab)
a1.set_xlabel("outdoor air temperature (°C)")
a1.set_ylabel("mass flow (kg/s)")
a2.set_xlabel("outdoor air temperature (°C)")
a2.set_ylabel("plate temperature (°C)")
a1.legend(frameon=False, fontsize=8)
fig.suptitle("Case 3: outdoor-temperature sensitivity (82 kWe, no wind)")
fig.tight_layout()
fig.savefig("fig4_weather_T.png")

ww = R["weather_wind"]
fig, ax = plt.subplots(figsize=(6.2, 4.0))
for tag, col, lab in (("favorable", GREEN, "stack suction (Cp = −0.3)"),
                      ("adverse", RED, "stack blockage (Cp = +0.3)")):
    rows = [r for r in ww if r["tag"] == tag]
    ax.plot([r["wind"] for r in rows], [r["m_dot"] for r in rows],
            "-o", ms=4, color=col, label=lab)
ax.set_xlabel("wind speed (m/s)")
ax.set_ylabel("mass flow (kg/s)")
ax.set_title("Case 3: wind effect on natural circulation (82 kWe, 2 °C)")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig("fig5_weather_wind.png")
print("figures written")

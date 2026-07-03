"""Independent order-of-magnitude checks on the detailed model (Case 1).

These deliberately use different, cruder methods than rccs_model.py:
a two-surface radiation enclosure and a single-node stack balance.
"""
import numpy as np

SIG = 5.670374419e-8
C0 = 273.15

# --- 1. Two-surface radiation enclosure: plate vs "riser plane" ----------
# Plate and an effective plane at the riser front, equal areas, connected by
# re-radiating side walls (Incropera three-surface network, eq. 13.30).
A = 9.13
eps1 = 0.785
# effective emissivity of the riser plane: 46% duct fronts (eps 0.8) + 54%
# gap apertures acting as deep cavities (apparent eps ~0.95)
eps2 = 0.462 * 0.80 + 0.538 * 0.95
F12 = 0.60          # crossed-strings, strips w=1.32 m apart d=0.71 m
F12_eff = F12 + (1 - F12) / 2.0            # re-radiating side walls
R = (1 - eps1) / eps1 + 1 / F12_eff + (1 - eps2) / eps2
Q = 73e3            # power reaching the risers (model: air pickup)
T2 = 200 + C0       # riser plane ~ area-weighted duct surface temperature
T1 = (T2 ** 4 + Q * R / (SIG * A)) ** 0.25
print(f"[1] two-surface enclosure: eps_plane={eps2:.2f}, R={R:.2f}")
print(f"    plate T for 73 kW with riser plane at 200 C -> {T1-C0:.0f} C "
      "(model: 423 C)")

# --- 2. Stack draft vs. riser friction, single hot column ----------------
T_hot = 90 + C0      # mean riser gas temp (model: ~84 C mid)
T_chim = 145 + C0
T_amb = 2 + C0
rho = lambda T: 101325 / 287.05 / T
dp_drive = 9.81 * ((rho(T_amb) - rho(T_hot)) * 6.9 / 2
                   + (rho(T_amb) - rho(T_hot)) * 6.9 / 2
                   + (rho(T_amb) - rho(T_chim)) * 11.2)
# losses ~ (fL/D + K) dynamic heads on riser velocity
m = 0.56
v = m / (rho(T_hot) * 0.121)
dp_loss = (0.026 * 106 + 1.8) * 0.5 * rho(T_hot) * v ** 2
print(f"[2] stack draft ~{dp_drive:.0f} Pa vs riser losses ~{dp_loss:.0f} Pa "
      f"at m=0.56 kg/s, v={v:.1f} m/s (should be comparable)")

# --- 3. Energy: dT from first law ----------------------------------------
dT = 73e3 / (0.564 * 1010)
print(f"[3] first-law riser dT = {dT:.0f} K (model: 128 K)")

# --- 4. Internal film temperature drop ------------------------------------
# mid-plane front-face flux: radiation ~5.4 kW/m2 absorbed on 0.61 m wide
# strip, redistributed over internal perimeter by conduction/re-radiation
q_int = 73e3 / (12 * 0.5713 * 6.91)   # mean internal flux, W/m2
h = 15.8
print(f"[4] mean internal flux {q_int:.0f} W/m2 -> wall-air dT ~ "
      f"{q_int/h:.0f} K (model mid-plane: front-air = "
      f"{215-84:.0f} K, sides {177-84:.0f} K)")

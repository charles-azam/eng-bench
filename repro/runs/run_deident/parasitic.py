"""
First-principles estimate of parasitic heat loss, to interpret the 82 kWe electric
input (Case 1) vs the scaled thermal duty (56 kWt). Conductive loss through the
insulated cavity walls + heater backing to building air (20 C).
"""
import numpy as np
IN=0.0254
# SuperIsol cavity walls (N/S/W), 6 in, k~0.09 W/mK at ~300C mean
k_si, t_si = 0.09, 6*IN
# Duraboard behind heaters, 2 in, k~0.09 at ~400C
k_db, t_db = 0.09, 2*IN

H, W, D = 6.7, 1.321, 0.7066
A_west = H*W                    # back wall
A_ns   = 2*(H*D)                # north+south
A_side_back = A_west + A_ns
A_heater_back = 10.18           # behind plate/heaters

# Reradiating cavity-wall inner face reaches ~ between plate(359) and riser(128): ~270C
Tw_in, Tbld = 270.0, 20.0
q_si = k_si*(Tw_in-Tbld)/t_si
Q_side_back = q_si*A_side_back

# Heater backing: heater ~ 420C behind plate, structure behind Duraboard ~50C
q_db = k_db*(420-50)/t_db
Q_heater_back = q_db*A_heater_back

# Uninsulated inlet plenum + downcomer convective loss (~small, warm surfaces ~30-40C):
Q_misc = 2.0e3

Q_par = Q_side_back + Q_heater_back + Q_misc
print(f"Side/back insulated walls: q''={q_si:.0f} W/m2 x {A_side_back:.1f} m2 = {Q_side_back/1e3:.1f} kW")
print(f"Heater backing (Duraboard): q''={q_db:.0f} W/m2 x {A_heater_back:.1f} m2 = {Q_heater_back/1e3:.1f} kW")
print(f"Misc uninsulated plenum/downcomer: {Q_misc/1e3:.1f} kW")
print(f"Total parasitic (first-principles) ~ {Q_par/1e3:.1f} kW")
print(f"=> heat to air if electric=82 kWe: {82-Q_par/1e3:.0f} kW")
print(f"   (facility implies 82-56=26 kW loss; our estimate is lower, so heat-to-air")
print(f"    plausibly 56-72 kW; we adopt the stated 56 kWt scaled duty as baseline.)")

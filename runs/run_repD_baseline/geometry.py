"""
NSTF-type RCCS 1/2-scale facility geometry, derived only from inputs/.
All values SI.  in->m factor 0.0254.
"""
import math

IN = 0.0254
FT = 0.3048

# ---- Risers (12 rectangular steel tubes, ASTM A500-B) ----
N_RISER = 12
riser_out_a = 10 * IN          # 0.254 m  (deep, plate->rear direction)
riser_out_b = 2 * IN           # 0.0508 m (wide face toward plate = FRONT face)
wall_t = 0.188 * IN            # 0.004775 m
riser_in_a = riser_out_a - 2 * wall_t   # 9.624 in internal
riser_in_b = riser_out_b - 2 * wall_t   # 1.624 in internal
A_riser_1 = riser_in_a * riser_in_b            # internal flow area, one duct
P_riser_in = 2 * (riser_in_a + riser_in_b)     # internal wetted perimeter
Dh_riser = 4 * A_riser_1 / P_riser_in          # hydraulic diameter
A_riser_tot = N_RISER * A_riser_1              # total internal flow area

L_riser_total = 295 * IN       # 7.493 m
L_riser_heated = 272 * IN      # 6.909 m  (inside heated cavity)
z_top = L_riser_heated         # heated column top elevation (riser bottom = 0)
z_mid = 3.500                  # instrumented mid-plane (Riser 7), z=3500 mm

# internal convective surface area over the heated length (all 12 ducts)
A_int_heated = P_riser_in * L_riser_heated * N_RISER
# front-face external area (line-of-sight to plate)
A_front_ext = riser_out_b * L_riser_heated * N_RISER

# ---- Heated plate (mock RPV, SAE 1020, east wall) ----
A_plate = 10.18                # as-built heated-plate area [m2]
eps_plate = 0.78
cavity_width = 52 * IN         # 1.321 m
cavity_height = 22 * FT        # 6.706 m
cavity_gap = 0.7066            # plate face -> riser front face [m] (baseline)
A_curtain = cavity_width * cavity_height   # cross-section "riser curtain" plane 8.84 m2

# ---- Riser surface emissivity (NOT reported in source) ----
eps_riser = 0.80               # oxidized structural steel, cited assumption

# ---- Downcomer (inlet, uninsulated 24 in dia) ----
D_down = 24 * IN               # 0.610 m
A_down = math.pi/4 * D_down**2
L_down = 184.5 * IN            # 4.686 m equivalent centerline
z_inlet = 4.686                # approx top-of-downcomer inlet elevation

# ---- Chimney (dual 24 in, insulated) ----
D_chim = 24 * IN
A_chim_tot = 0.58              # baseline total chimney flow area [m2]
L_chim_vert = 826 * IN         # 20.98 m
L_chim_horiz = 470 * IN        # 11.94 m
L_chim = L_chim_vert + L_chim_horiz
z_discharge = 19.6             # baseline discharge height [m]
z_outlet_plenum_top = z_top + 74*IN   # outlet plenum 74 in tall

# ---- Steel property ----
k_steel = 50.0                 # W/m/K

# ---- Insulation (parasitic loss) ----
t_super = 6 * IN               # 0.152 m SuperIsol on N/S/W cavity walls
k_super = 0.09                 # W/m/K (~500 C mean)
t_dura = 2 * IN                # 0.051 m Duraboard behind heaters
k_dura = 0.11                  # W/m/K (~700 C)
A_side_walls = 2 * (cavity_gap * cavity_height)   # N + S walls
A_back_wall = cavity_width * cavity_height         # W wall behind risers
A_wall_ins = A_side_walls + A_back_wall            # SuperIsol area
A_dura = A_plate                                   # behind the heated plate

if __name__ == "__main__":
    print(f"A_riser_1   = {A_riser_1*1e4:.2f} cm2  (target 101 cm2)")
    print(f"Dh_riser    = {Dh_riser*1000:.2f} mm   (target ~70.7 mm)")
    print(f"A_riser_tot = {A_riser_tot:.4f} m2")
    print(f"A_int_heated= {A_int_heated:.2f} m2")
    print(f"A_front_ext = {A_front_ext:.2f} m2")
    print(f"A_curtain   = {A_curtain:.2f} m2")
    print(f"A_down      = {A_down:.4f} m2")
    print(f"A_wall_ins  = {A_wall_ins:.2f} m2  A_dura = {A_dura:.2f} m2")

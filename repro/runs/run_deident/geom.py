"""
Facility geometry, derived entirely from inputs/01_facility_geometry.md.
All SI. Conversions: 1 in = 0.0254 m, 1 ft = 0.3048 m.
"""
import numpy as np

IN = 0.0254
g = 9.81

# ---- Risers (12 vertical rectangular steel ducts) ----
N_RISER = 12
r_out_a, r_out_b = 10*IN, 2*IN          # outer cross-section 10 in x 2 in
wall_t = 0.188*IN                        # wall thickness
r_in_a = r_out_a - 2*wall_t              # internal long dim  (9.624 in)
r_in_b = r_out_b - 2*wall_t              # internal short dim (1.624 in)
A_duct = r_in_a * r_in_b                 # internal flow area per duct [m2]
P_duct = 2*(r_in_a + r_in_b)             # internal wetted perimeter [m]
Dh = 4*A_duct / P_duct                   # hydraulic diameter [m]
A_flow_total = N_RISER * A_duct          # total internal flow area [m2]

L_riser_total = 295*IN                   # 7.49 m total
L_riser_heated = 272*IN                  # 6.91 m inside heated cavity
H_riser = L_riser_total                  # buoyant riser column height (bottom->top)

# Internal heat-transfer surface per duct over heated length:
A_riser_inner_heated = P_duct * L_riser_heated          # per duct [m2]
A_riser_inner_total  = N_RISER * A_riser_inner_heated    # all 12 ducts

# Riser front face (2-in narrow face, line-of-sight to plate) over heated length:
w_front = r_out_b                        # 2 in outer width of narrow face
A_front_face_total = N_RISER * w_front * L_riser_heated  # projected front area

# ---- Heated plate (mock RPV) ----
# As-built ~10.18 m2; scaling line lists 8.82 m2. Use as-built, note sensitivity.
A_plate = 10.18                          # m2 (front radiating face)
H_cavity = 6.7                           # m (22 ft)
W_cavity = 52*IN                         # 1.321 m
cavity_depth = 27.82*IN                  # 0.7066 m baseline plate->riser-front spacing

# ---- Downcomer (inlet, 24-in dia, uninsulated) ----
D_dc = 24*IN
A_dc = np.pi/4*D_dc**2
L_dc = 184.5*IN                          # equivalent centerline length

# ---- Chimney (dual 24-in stacks, insulated) ----
D_ch = 24*IN
A_ch_total = 0.58                        # baseline chimney flow area [m2] (given)
L_ch_vert = 826*IN
L_ch_horiz = 470*IN
H_discharge = 19.6                       # baseline discharge height [m]

# Effective buoyant stack height above the riser top (outlet plenum + chimney rise)
H_stack_above_riser = H_discharge - H_riser   # ~12.1 m

if __name__ == "__main__":
    print(f"A_duct={A_duct:.5f} m2  P_duct={P_duct:.4f} m  Dh={Dh:.5f} m")
    print(f"A_flow_total={A_flow_total:.4f} m2")
    print(f"A_riser_inner_total={A_riser_inner_total:.3f} m2")
    print(f"A_front_face_total={A_front_face_total:.3f} m2")
    print(f"A_dc={A_dc:.4f} m2  A_ch_total={A_ch_total:.3f} m2")
    print(f"H_riser={H_riser:.3f}  H_stack_above_riser={H_stack_above_riser:.3f}")

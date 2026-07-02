"""Facility geometry, derived strictly from inputs/01_facility_geometry.md.
All SI. Sources noted inline."""
import numpy as np

IN = 0.0254   # m per inch
FT = 0.3048

# --- Riser ducts (12) : outer 10x2 in, wall 0.188 in -> internal 9.624 x 1.624 in
N_RISER   = 12
r_a = 9.624*IN          # internal long dim  = 0.24445 m
r_b = 1.624*IN          # internal short dim = 0.04125 m
A_RISER_1 = r_a*r_b                       # 0.010084 m^2
A_RISER   = N_RISER*A_RISER_1             # total internal flow area
P_RISER_1 = 2*(r_a+r_b)                   # internal wetted perimeter, one duct
DH_RISER  = 4*A_RISER_1/P_RISER_1         # hydraulic diameter
L_RISER_TOT = 295*IN                      # 7.493 m total
L_RISER_CAV = 272*IN                      # 6.909 m inside cavity (heated span)
WALL_RISER  = 0.188*IN                    # 4.78 mm steel wall

# heated exchange length ~ plate height 6.7 m; risers span 6.909 m in cavity
L_HEAT = 6.7                              # m, heated plate height (cavity height 22 ft)

# internal wetted heated area (all 12 risers, all four faces, over heated height)
A_INT_WET = N_RISER*P_RISER_1*L_HEAT      # m^2

# per-face internal widths (for face-resolved reporting)
FACE_FRONT_W = r_b   # narrow face (line of sight to plate), internal 0.04125 m
FACE_SIDE_W  = r_a   # wide face

# outer riser front-face area (narrow face, line of sight to plate)
FRONT_W_OUT = 2.0*IN
A_FRONT_OUT = N_RISER*FRONT_W_OUT*L_HEAT

# --- Heated plate (mock RPV)
A_PLATE = 10.18          # m^2 as-built (input 01 sec 3)
PLATE_W = 52*IN          # cavity width 1.321 m
PLATE_H = 6.7            # m
PLATE_THK = 1.0*IN       # 25.4 mm SAE1020
EPS_PLATE = 0.785        # measured 0.78-0.79

# --- Cavity
CAV_GAP  = 0.7066        # m plate front -> riser front face (baseline)
CAV_W    = 52*IN         # 1.321 m
CAV_H    = 6.7           # m

# --- riser emissivity (NOT reported -> oxidized structural steel assumption)
EPS_RISER = 0.80         # oxidized ASTM A500; assumption, range 0.7-0.9

# --- Chimney / stacks (dual 24-in, insulated)
D_CHIM   = 24*IN         # 0.6096 m each
A_CHIM   = 0.58          # m^2 baseline (both stacks; input says 0.58)
H_DISCHARGE = 19.6       # m baseline discharge height
# equivalent flow lengths from outlet plenum (per input 6): vertical 826in, horiz 470in
L_CHIM_EQ = (826+470)*IN # 32.9 m equivalent, split between two stacks

# --- Downcomer (single 24-in, uninsulated)
D_DOWN = 24*IN
A_DOWN = np.pi/4*D_DOWN**2       # 0.2919 m^2
L_DOWN_EQ = 184.5*IN             # 4.69 m

# --- plena
# inlet plenum ~ z=0 (bottom); outlet plenum ceiling; risers z=0..6.909
Z_RISER_BOT = 0.0
Z_RISER_TOP = L_RISER_CAV        # ~6.909
Z_DISCHARGE = H_DISCHARGE        # 19.6

# steel props
K_STEEL = 50.0
RHO_STEEL = 7850.0
CP_STEEL = 480.0

if __name__ == "__main__":
    print(f"A_RISER_1 = {A_RISER_1:.5f} m2 (input ~0.0101)")
    print(f"DH_RISER  = {DH_RISER:.5f} m (input ~0.0707)")
    print(f"A_RISER   = {A_RISER:.5f} m2 total (12 ducts)")
    print(f"A_INT_WET = {A_INT_WET:.3f} m2 internal heated wetted")
    print(f"A_FRONT_OUT = {A_FRONT_OUT:.3f} m2 riser front faces (outer)")
    print(f"A_DOWN = {A_DOWN:.4f} m2, A_CHIM={A_CHIM}")

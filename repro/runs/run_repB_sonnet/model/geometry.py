"""
Facility geometry, encoded from inputs/01_facility_geometry.md.
All values traceable to that file; derived quantities are computed here with the
derivation shown (do not hand-copy anything not explicitly given).
"""
import numpy as np

IN = 0.0254  # m per inch

# ---------------------------------------------------------------- cavity ----
CAVITY_HEIGHT = 6.7          # m  (22 ft, "cavity height")
CAVITY_WIDTH = 52 * IN       # m  (1.3208 m)
CAVITY_DEPTH_BASELINE = 70.66e-2  # m  (706.6 mm, riser-front-to-plate)
PLATE_AREA_AS_BUILT = 10.18   # m^2  (as-built heated-plate area)
PLATE_AREA_SCALING_TABLE = 8.82  # m^2  (Table-4 scaling-line value; ~12% lower;
                                   # source itself flags this as an inconsistency)
# We use the as-built area for the physical plate temperature calc (Task choice,
# stated as an assumption in the calc note) and keep the scaling-table value only
# for cross-checking heat flux against the source's own stated design fluxes.

# --------------------------------------------------------- heated plate -----
PLATE_THICKNESS = 1 * IN     # m (25.4 mm)
PLATE_EMISSIVITY = 0.785     # mid of measured 0.78-0.79
PLATE_K = 50.0                # W/m/K, SAE1020 steel (inputs/02, "typical")
PLATE_RHO = 7850.0
PLATE_CP = 480.0

# --------------------------------------------------------------- risers -----
N_RISERS = 12
RISER_OD_WIDE = 10 * IN      # m, outer "wide" face (0.254 m)
RISER_OD_NARROW = 2 * IN     # m, outer "narrow" face (0.0508 m) -- front/rear
RISER_WALL_T = 0.188 * IN    # m (0.004775 m)
RISER_ID_WIDE = RISER_OD_WIDE - 2 * RISER_WALL_T    # 0.24445 m (~9.624 in given)
RISER_ID_NARROW = RISER_OD_NARROW - 2 * RISER_WALL_T  # 0.04125 m (~1.624 in given)
RISER_FLOW_AREA_1 = RISER_ID_WIDE * RISER_ID_NARROW   # single-duct internal area
RISER_FLOW_AREA_TOTAL = N_RISERS * RISER_FLOW_AREA_1
RISER_PERIM_INNER = 2 * (RISER_ID_WIDE + RISER_ID_NARROW)
RISER_DH = 4 * RISER_FLOW_AREA_1 / RISER_PERIM_INNER   # hydraulic diameter, single duct
RISER_LENGTH_TOTAL = 295 * IN     # m, 7.493 m
RISER_LENGTH_HEATED = 272 * IN    # m, 6.9088 m, inside the heated cavity
RISER_LENGTH_BELOW = 7 * IN       # protrusion into inlet plenum
RISER_LENGTH_ABOVE = 16 * IN      # protrusion into outlet plenum
RISER_EMISSIVITY = 0.80           # ASSUMPTION: oxidized structural steel, not
                                    # reported in source; typical range 0.79-0.82
                                    # (Incropera Table A.11, "steel, oxidized").
RISER_K = 50.0
RISER_RHO = 7850.0
RISER_CP = 480.0

RISER_OUTER_PERIM = 2 * (RISER_OD_WIDE + RISER_OD_NARROW)
RISER_FRONT_FACE_AREA_1 = RISER_OD_NARROW * RISER_LENGTH_HEATED  # one riser, front face
RISER_FRONT_FACE_AREA_TOTAL = N_RISERS * RISER_FRONT_FACE_AREA_1
RISER_INNER_HT_AREA_TOTAL = N_RISERS * RISER_PERIM_INNER * RISER_LENGTH_HEATED

# Riser pitch: "not numerically specified" except "~4.3 in nominal" across the
# 52-in cavity width for 12 ducts -> use that nominal value explicitly (flagged).
RISER_PITCH = 4.3 * IN
RISER_ROW_WIDTH = N_RISERS * RISER_OD_WIDE  # ducts sit with 10-in wide faces
# facing neighbours; if pitch (center-to-center) ~4.3in < wide face 10in this
# is geometrically impossible with wide-face-to-wide-face packing, so the "52 in"
# cavity width most likely refers to the depth-wise/other orientation; treat the
# riser row as spanning very close to the full 52 in cavity width (consistent
# with "sit in a row across the 52-in cavity width"). We therefore take the
# riser row width = cavity width = 1.3208 m for view-factor geometry, which is
# the only self-consistent reading of the source text. (Flagged as an
# ambiguity/assumption -- see calc note.)

# --------------------------------------------------- inlet downcomer/plenum --
DOWNCOMER_D = 24 * IN
DOWNCOMER_AREA = np.pi / 4 * DOWNCOMER_D ** 2
DOWNCOMER_LEN_EQUIV = 184.5 * IN

INLET_PLENUM_H = 44 * IN
INLET_PLENUM_W = 51.75 * IN
INLET_PLENUM_DEPTH = 31.75 * IN
INLET_PLENUM_VOL = 1.18  # m^3, given directly

# -------------------------------------------------------------- outlet plenum
OUTLET_PLENUM_H = 74 * IN
OUTLET_PLENUM_EW = 74 * IN
OUTLET_PLENUM_NS = 64 * IN
OUTLET_PLENUM_VOL = 5.77  # m^3, given directly
CHIMNEY_PORT_D = 24 * IN
CHIMNEY_PORT_Z_ABOVE_FLOOR = 56.5 * IN
CHIMNEY_PORT_Z_ABOVE_RISERTOP = 40.5 * IN

# ------------------------------------------------------------------ chimney --
CHIMNEY_D = 24 * IN
N_CHIMNEYS = 2
CHIMNEY_AREA_EACH = np.pi / 4 * CHIMNEY_D ** 2
CHIMNEY_AREA_TOTAL_BASELINE = 0.58  # m^2, given directly (baseline)
CHIMNEY_VERT_LEN = 826 * IN    # m, equivalent vertical run (per chimney)
CHIMNEY_HORIZ_LEN = 470 * IN   # m, equivalent horizontal run (per chimney)
CHIMNEY_DISCHARGE_HEIGHT_BASELINE = 19.6  # m, ABOVE... (datum ambiguous, see note)
CHIMNEY_DISCHARGE_HEIGHT_MIN = 7.7

# ---------------------------------------------------- axial elevation datum -
# z = 0 at riser bottom (heated-section bottom), per inputs/01 Sec.8.
Z_RISER_BOTTOM = 0.0
Z_RISER_TOP = RISER_LENGTH_HEATED  # 6.909 m
Z_OUTLET_PLENUM_FLOOR = Z_RISER_TOP - RISER_LENGTH_ABOVE
Z_OUTLET_PLENUM_PORT = Z_OUTLET_PLENUM_FLOOR + CHIMNEY_PORT_Z_ABOVE_FLOOR  # 7.94 m
Z_CHIMNEY_EXIT = CHIMNEY_DISCHARGE_HEIGHT_BASELINE  # taken relative to same datum
# (ASSUMPTION: "discharge height" in the source is measured from the same base
# elevation as the riser bottom / grade; the 826 in "vertical equivalent length"
# for the chimney is used only for FRICTION (total path length), not for the net
# buoyancy elevation gain, because it is explicitly an "equivalent centerline
# length" that can include fitting allowances. This is flagged as a key
# geometric assumption in the calc note.)

if __name__ == "__main__":
    print("Riser Dh =", RISER_DH, "m (source states 0.0707 m)")
    print("Riser flow area total =", RISER_FLOW_AREA_TOTAL, "m^2 (source: 0.0101*12=0.1212)")
    print("Riser front face area total =", RISER_FRONT_FACE_AREA_TOTAL, "m^2")
    print("Riser inner HT area total =", RISER_INNER_HT_AREA_TOTAL, "m^2")
    print("Downcomer area =", DOWNCOMER_AREA, "m^2")
    print("Chimney area each =", CHIMNEY_AREA_EACH, "m^2, x2 =", 2*CHIMNEY_AREA_EACH)
    print("Z chimney exit (assumed datum) =", Z_CHIMNEY_EXIT)
    print("Z outlet plenum port =", Z_OUTLET_PLENUM_PORT)

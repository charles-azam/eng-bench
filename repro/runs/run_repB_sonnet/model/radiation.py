"""
Radiation exchange between the heated plate (mock RPV) and the riser front
faces, treated as a 2-surface + adiabatic-reradiating-surface enclosure.

Method:
  1. Direct view factor F12 between two aligned, parallel, directly-opposed
     rectangles (the plate, and the full opposite plane at the riser-front
     distance), closed-form solution -- Incropera & DeWitt, "Fundamentals of
     Heat and Mass Transfer," 6th ed., Table 13.2 / Eq. 13.6 (equivalent to
     Modest, "Radiative Heat Transfer," Table 4.1, config. "parallel rects").
  2. The riser front faces cover only a fraction of that opposite plane (12
     narrow strips out of the full width); F(plate->riser fronts) is taken
     proportional to the covered area fraction -- an approximation, stated as
     an assumption (reasonable because the 12 strips are evenly distributed
     over the full plate height and width).
  3. The N/S/W cavity walls are insulated/adiabatic -> treated as a single
     reradiating surface completing a 3-surface enclosure (Incropera & DeWitt
     Eq. 13.32, "two surfaces exchanging via a reradiating surface").
"""
import numpy as np
from air_properties import SIGMA


def view_factor_parallel_rects(a, b, c):
    """Direct view factor between two aligned, parallel rectangles of size
    (a x b), separated by distance c (Incropera & DeWitt Table 13.2)."""
    X, Y = a / c, b / c
    p = np.sqrt(1 + X**2)
    q = np.sqrt(1 + Y**2)
    term1 = np.log((p**2 * q**2) / (p**2 + q**2 - 1))
    term2 = X * q * np.arctan(X / q)
    term3 = Y * p * np.arctan(Y / p)
    term4 = -X * np.arctan(X)
    term5 = -Y * np.arctan(Y)
    F = (2.0 / (np.pi * X * Y)) * (0.5 * term1 + term2 + term3 + term4 + term5)
    return F


def plate_to_riserfront_view_factor(cavity_width, cavity_height, gap,
                                     riser_front_area_total):
    """F12: plate -> riser front faces, via the area-fraction approximation
    described in the module docstring."""
    A_plane = cavity_width * cavity_height
    F_full = view_factor_parallel_rects(cavity_width, cavity_height, gap)
    area_frac = riser_front_area_total / A_plane
    F12 = F_full * area_frac
    return F12, F_full, area_frac


def three_surface_exchange(T1, T2, A1, A2, F12, eps1, eps2):
    """Net radiative heat transfer rate [W] from surface 1 (plate) to surface 2
    (riser fronts), with the remainder of the enclosure a reradiating surface.
    Incropera & DeWitt Eq. 13.32."""
    F1R = 1.0 - F12
    F21 = A1 * F12 / A2
    F2R = 1.0 - F21
    Eb1 = SIGMA * T1**4
    Eb2 = SIGMA * T2**4

    R1 = (1 - eps1) / (eps1 * A1)
    R2 = (1 - eps2) / (eps2 * A2)
    R12 = 1.0 / (A1 * F12)
    R1R = 1.0 / (A1 * F1R)
    R2R = 1.0 / (A2 * F2R)
    # parallel combination of the direct path (R12) and the via-reradiating
    # path (R1R + R2R in series)
    R_mid = 1.0 / (1.0 / R12 + 1.0 / (R1R + R2R))
    R_total = R1 + R_mid + R2
    q = (Eb1 - Eb2) / R_total
    return q


if __name__ == "__main__":
    import geometry as G
    F12, F_full, frac = plate_to_riserfront_view_factor(
        G.CAVITY_WIDTH, G.CAVITY_HEIGHT, G.CAVITY_DEPTH_BASELINE,
        G.RISER_FRONT_FACE_AREA_TOTAL)
    print(f"F_full (plate->opposite plane) = {F_full:.4f}")
    print(f"area fraction covered by riser fronts = {frac:.4f}")
    print(f"F12 (plate->riser fronts) = {F12:.4f}")
    q = three_surface_exchange(600+273.15, 300+273.15, 8.82,
                                G.RISER_FRONT_FACE_AREA_TOTAL, F12,
                                G.PLATE_EMISSIVITY, G.RISER_EMISSIVITY)
    print(f"q(600C plate, 300C riser front) = {q/1000:.2f} kW")

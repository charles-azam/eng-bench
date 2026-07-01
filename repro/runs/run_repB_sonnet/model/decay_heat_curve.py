"""
Case 2 decay-heat power curve.

The input file (inputs/04) gives a 10th-order polynomial fit (C0-C9) to a
"digitized reactor RCCS removal curve," but explicitly notes the C10 term is
missing from the source and offers a fallback: "impose the normalized shape:
26 -> 56 kWt rise over ~85 h, peak at 84.85 h, then decay."

We checked the polynomial directly (see check_polynomial() below): evaluated
in minutes (as its own units note states) it gives P(0)=42.0 kWt (not the
stated 26.16 kWt) and peaks near t=72 h at 87.7 kWt (not 56.07 kWt at 84.85 h),
then diverges to large negative power beyond ~t=110 h -- consistent with the
source's admission that the truncated (C10-missing) polynomial does not fully
reproduce the intended curve. We therefore use the explicitly-sanctioned
fallback: a smooth analytic curve built to match the three stated control
points (initial level, peak level & time, decaying afterward). This is
DOCUMENTED AS AN ASSUMPTION (the exact rise/decay shape between control
points, and the post-peak decay time constant, are not given in the inputs).
"""
import numpy as np

C = [466.531039994, 0.078631095079, 0.000170562320568, -1.28449427566e-07,
     5.09424812301e-11, -1.27606140005e-14, 2.04789514471e-18,
     -2.08318254453e-22, 1.29530038954e-26, -4.48601180685e-31]


def polynomial_curve_kWt(t_hours):
    """Direct evaluation of the source's polynomial (t in minutes per its
    stated units); returns kWt. Included for the record / transparency."""
    t_min = t_hours * 60.0
    s = sum(c * t_min ** n for n, c in enumerate(C))
    return s * 90.0 / 1000.0


def check_polynomial():
    print("Direct polynomial check (t in minutes):")
    for h in [0, 24, 48, 72, 84.85, 90, 100, 110, 120]:
        print(f"  t={h:7.2f} h -> P={polynomial_curve_kWt(h):9.2f} kWt")


P0_KWT = 26.16     # normal-operation ½-scale power (given)
PPEAK_KWT = 56.07  # peak accident ½-scale power (given)
T_PEAK_H = 84.85   # ½-scale time of peak (given)
TAU_DECAY_H = 200.0  # ASSUMED post-peak decay time constant (not given in
                      # inputs; order-of-magnitude typical of the slow decline
                      # phase of a reactor decay-heat curve on a multi-day
                      # timescale -- flagged as an assumption)


def decay_heat_kWt(t_hours):
    """Smooth normalized curve through the three given control points."""
    t = np.asarray(t_hours, dtype=float)
    rise = P0_KWT + (PPEAK_KWT - P0_KWT) * 0.5 * (1 - np.cos(np.pi * np.minimum(t, T_PEAK_H) / T_PEAK_H))
    decay_extra = np.where(t > T_PEAK_H,
                            PPEAK_KWT * np.exp(-(t - T_PEAK_H) / TAU_DECAY_H) - PPEAK_KWT,
                            0.0)
    return rise + decay_extra


if __name__ == "__main__":
    check_polynomial()
    print()
    print("Fallback normalized shape (control points: 26.16 kWt @ t=0, "
          "56.07 kWt @ t=84.85h, then exp decay tau=200h):")
    for h in [0, 12, 24, 48, 72, 84.85, 100, 150, 200, 300, 400]:
        print(f"  t={h:7.2f} h -> P={decay_heat_kWt(h):7.2f} kWt")

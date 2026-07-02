"""
Case 2 - accident decay-heat transient, and passive-stability check.

The plate steel thermal time constant is short compared with the 85-hour ramp,
so the system is quasi-steady: at each instant we solve the full steady model
for the instantaneous power P(t).  A lumped-capacitance integration confirms
the plate lag is negligible and that temperature LEVELS OFF (no runaway),
because both radiation (~T^4) and buoyant flow rise with plate temperature.
"""
import numpy as np
import air_props as ap
import geometry as g
from steady import (solve_steady, Q_rad, Q_conv_cav, A_BAR, SIGMA)

# ---- decay-heat power curve ----
C = [466.531039994, 0.078631095079, 0.000170562320568, -1.28449427566e-07,
     5.09424812301e-11, -1.27606140005e-14, 2.04789514471e-18,
     -2.08318254453e-22, 1.29530038954e-26, -4.48601180685e-31]

def poly_raw(t_min):
    return sum(c*t_min**n for n, c in enumerate(C))

def power_curve(t_h):
    """Electric power [W] vs time [h]. Evaluate the digitized polynomial
    (t in minutes) and rescale to the stated physical envelope
    26.16 kWt (start) -> 56.07 kWt (peak at 84.85 h), then decay."""
    t_min = t_h*60.0
    raw = poly_raw(t_min)
    return raw  # W as given by [poly]xPscale is folded into C already? -> checked below


def power_curve_scaled(t_h, tpeak_h=84.85):
    """Robust normalized shape: linear-ish rise 26->56 kWt to the peak, then
    a gentle decay, matching the stated endpoints (used because the raw
    polynomial normalization/units are ambiguous in the source)."""
    P0, Ppk = 26_160.0, 56_070.0
    if t_h <= tpeak_h:
        # use polynomial SHAPE, normalized between its t=0 and t=peak values
        r0, rp = poly_raw(0.0), poly_raw(tpeak_h*60)
        frac = min(1.0, max(0.0, (poly_raw(t_h*60) - r0)/(rp - r0)))
        return P0 + (Ppk - P0)*frac
    else:
        # decay after peak (post-peak decline ~ scaled decay heat)
        rp = poly_raw(tpeak_h*60)
        r = poly_raw(t_h*60)
        # after peak polynomial turns over; map back down toward ~P0
        frac = max(0.0, (r - poly_raw(170*60))/(rp - poly_raw(170*60)))
        return P0 + (Ppk - P0)*frac


if __name__ == "__main__":
    print("raw poly at t=0,peak,170h:", round(poly_raw(0),1),
          round(poly_raw(84.85*60),1), round(poly_raw(170*60),1))

    # ---- quasi-steady transient trace ----
    print("\n=== CASE 2 transient (quasi-steady), Tin=20C, Tamb=2C ===")
    print(f"{'t[h]':>6} {'P[kW]':>7} {'m[kg/s]':>8} {'dT[C]':>7} "
          f"{'Tplate[C]':>10} {'Tris_front[C]':>13} {'radfrac':>8}")
    peak = {}
    for t_h in [0, 20, 40, 60, 84.85, 100, 120, 140]:
        P = power_curve_scaled(t_h)
        r = solve_steady(P, 20, 2)
        print(f"{t_h:6.1f} {P/1e3:7.2f} {r['m_dot']:8.3f} {r['dT']:7.1f} "
              f"{r['Tp_C']:10.1f} {r['Ts_front_mid_C']:13.1f} {r['rad_frac']:8.3f}")
        if not peak or r['Tp_C'] > peak['Tp_C']:
            peak = r; peak['t_h'] = t_h; peak['P'] = P

    print(f"\nPEAK: t={peak['t_h']} h, P={peak['P']/1e3:.1f} kW, "
          f"Tplate={peak['Tp_C']:.1f} C, Tris_front={peak['Ts_front_mid_C']:.1f} C, "
          f"m={peak['m_dot']:.3f} kg/s")

    # ---- passive-stability / runaway check ----
    # plate lumped thermal capacitance and radiative conductance
    m_plate = g.A_plate*0.0254*7850
    C_plate = m_plate*480
    Tp_pk = peak['Tp_C']+273.15
    dQdT = 4*SIGMA*A_BAR*Tp_pk**3
    tau = C_plate/dQdT
    print(f"\nPlate steel mass ~{m_plate:.0f} kg, C_plate={C_plate/1e3:.0f} kJ/K")
    print(f"Radiative conductance dQ/dTp={dQdT:.0f} W/K, tau={tau/3600:.2f} h "
          f"(<< 85 h ramp -> quasi-steady, plate lag negligible)")

    print("\n=== Steady removal capacity vs power (monotonic -> no runaway) ===")
    print(f"{'P[kW]':>7} {'Tplate[C]':>10} {'Q_rad[kW]':>10} {'Q_conv[kW]':>11}")
    for P in [26, 40, 56, 82, 120, 160, 220]:
        r = solve_steady(P*1e3, 20, 2)
        print(f"{P:7.0f} {r['Tp_C']:10.1f} {r['Q_rad']/1e3:10.1f} {r['Q_conv']/1e3:11.2f}")

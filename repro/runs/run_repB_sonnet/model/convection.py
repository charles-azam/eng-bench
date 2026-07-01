"""
Convection correlations used in the RCCS loop model.

(A) Cavity-side natural convection: sealed, tall vertical rectangular enclosure
    between the heated plate and the riser front-face plane.
    Catton (1978) / ElSherbiny et al. (1982) correlations as tabulated in
    Incropera & DeWitt, "Fundamentals of Heat and Mass Transfer," Table 9.3.

(B) Riser-internal convection: forced/buoyancy-driven duct flow inside the
    riser tubes (the actual natural-circulation coolant).
    - Laminar, uniform wall heat flux: Nu_Dh = 4.36 (circular-tube result used
      as an engineering approximation for the high-aspect-ratio rectangular
      duct; Incropera & DeWitt Table 8.1 shows the true rectangular-duct value
      is 40-70% higher at this aspect ratio (b/a~6), so this is a conservative
      (over-predicts wall-air dT) choice, stated as an assumption.)
    - Turbulent: Gnielinski (1976) correlation.
    - Transition 2300<Re<4000: linear blend.

(C) Darcy friction factor for the momentum balance: laminar f=64/Re; turbulent
    via Haaland's (1983) explicit approximation to Colebrook-White.
"""
import numpy as np


def rayleigh_gap(T_hot, T_cold, gap, T_film, rho, mu, cp, k, beta, g=9.80665):
    nu = mu / rho
    alpha = k / (rho * cp)
    Ra = g * beta * abs(T_hot - T_cold) * gap**3 / (nu * alpha)
    return Ra


def nu_cavity_enclosure(Ra_L, Pr, aspect_H_over_L):
    """Vertical rectangular enclosure Nu, Incropera & DeWitt Table 9.3."""
    HL = aspect_H_over_L
    if 1 <= HL <= 2:
        Nu = 0.18 * (Pr / (0.2 + Pr) * Ra_L) ** 0.29
    elif 2 < HL <= 10:
        Nu = 0.22 * (Pr / (0.2 + Pr) * Ra_L) ** 0.28 * HL ** (-0.25)
    else:
        # ElSherbiny et al. (1982), 10 < H/L <= 40, 1 <= Pr <= 2e4,
        # 1e4 <= Ra_L <= 1e7 — take the max of three sub-correlations.
        Nu1 = 0.0605 * Ra_L ** (1.0 / 3.0)
        Nu2 = (1 + (0.104 * Ra_L**0.293 / (1 + (6310.0 / Ra_L) ** 1.36)) ** 3) ** (1.0 / 3.0)
        Nu3 = 0.242 * (Ra_L / HL) ** 0.272
        Nu = max(Nu1, Nu2, Nu3)
    return max(Nu, 1.0)  # Nu can't be < pure-conduction (=1) in this formulation


def h_cavity_natural_convection(T_hot, T_cold, gap, height, width, air_props_fn):
    """Returns (h [W/m^2/K] referenced to the gap temperature difference,
    Ra_L, Nu) for the sealed plate<->riser-front cavity."""
    T_film = 0.5 * (T_hot + T_cold)
    rho, mu, cp, k, Pr, beta = air_props_fn(T_film)
    Ra_L = rayleigh_gap(T_hot, T_cold, gap, T_film, rho, mu, cp, k, beta)
    HL = height / gap
    Nu = nu_cavity_enclosure(Ra_L, Pr, HL)
    h = Nu * k / gap
    return h, Ra_L, Nu


def darcy_friction_factor(Re, roughness_ratio):
    """Darcy (Moody) friction factor. Laminar 64/Re; turbulent Haaland (1983)."""
    Re = np.maximum(Re, 1.0)
    f_lam = 64.0 / Re
    with np.errstate(divide="ignore", invalid="ignore"):
        f_turb = (-1.8 * np.log10(roughness_ratio / 3.7 +
                                   6.9 / Re)) ** -2
    if np.isscalar(Re):
        if Re < 2300:
            return f_lam
        elif Re > 4000:
            return f_turb
        else:
            w = (Re - 2300) / (4000 - 2300)
            return (1 - w) * f_lam + w * f_turb
    else:
        f = np.where(Re < 2300, f_lam, f_turb)
        return f


def nu_gnielinski(Re, Pr):
    f = (0.79 * np.log(Re) - 1.64) ** -2
    Nu = (f / 8) * (Re - 1000) * Pr / (1 + 12.7 * np.sqrt(f / 8) * (Pr ** (2.0 / 3) - 1))
    return Nu


def nu_riser_internal(Re, Pr):
    """Blend laminar (4.36) -> Gnielinski turbulent across 2300-4000."""
    Nu_lam = 4.36
    if Re < 2300:
        return Nu_lam
    Nu_turb = nu_gnielinski(max(Re, 3000.0), Pr)
    if Re > 4000:
        return nu_gnielinski(Re, Pr)
    w = (Re - 2300) / (4000 - 2300)
    return (1 - w) * Nu_lam + w * Nu_turb


def h_wind_external(V_wind):
    """External forced-convection coefficient for a surface exposed to
    outdoor wind. Jurges' formula (1924), widely used in building-physics /
    HVAC practice for wind-driven exterior surface convection:
    h = 5.7 + 3.8*V  [W/m^2/K], V in m/s (V<5 m/s regime; also used as a
    common engineering approximation beyond that range)."""
    return 5.7 + 3.8 * V_wind

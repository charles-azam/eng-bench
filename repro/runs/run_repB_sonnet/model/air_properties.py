"""
Air thermophysical properties at ~1 atm, built from generic (non-facility-specific)
physics/textbook correlations:

  - rho(T):   ideal gas law, R_specific = 287.05 J/kg/K
  - mu(T):    Sutherland's law (White, "Viscous Fluid Flow"; also NASA RP-1311).
              mu = mu_ref * (T_ref+S)/(T+S) * (T/T_ref)^1.5
              mu_ref = 1.716e-5 Pa.s @ T_ref=273.15 K, S = 110.4 K  (air)
  - cp(T):    linear fit anchored to Incropera & DeWitt, "Fundamentals of Heat and
              Mass Transfer," Table A.4 (air, 1 atm): cp=1007 J/kg/K @300K,
              cp=1141 J/kg/K @1000K -> slope 0.1914 J/kg/K^2.
  - Pr(T):    piecewise-linear interpolation of the same Table A.4 anchor values
              (Pr is a weak function of T for air; anchors below).
  - k(T):     back out from k = mu*cp/Pr (self-consistent with the above).
  - beta(T):  ideal-gas thermal expansion coefficient, beta = 1/T.

These are generic open-literature correlations for dry air, not measurements or
model outputs from the facility being analyzed.
"""
import numpy as np

R_AIR = 287.05      # J/kg/K
P_ATM = 101325.0    # Pa (facility ~1 atm, per inputs/02)
G = 9.80665         # m/s^2
SIGMA = 5.670374e-8 # Stefan-Boltzmann, W/m^2/K^4

# Table A.4-style anchors (Incropera & DeWitt), used only for the Pr(T) trend.
_T_ANCH = np.array([250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800,
                     850, 900, 950, 1000, 1100, 1200])
_PR_ANCH = np.array([0.720, 0.707, 0.700, 0.690, 0.686, 0.684, 0.684, 0.685,
                      0.690, 0.695, 0.702, 0.709, 0.716, 0.720, 0.723, 0.726,
                      0.728, 0.728])


def mu_air(T):
    """Sutherland's law, T in K, returns Pa.s."""
    T_ref, S, mu_ref = 273.15, 110.4, 1.716e-5
    return mu_ref * (T_ref + S) / (T + S) * (T / T_ref) ** 1.5


def cp_air(T):
    """J/kg/K, linear fit anchored to Incropera Table A.4 (300K, 1000K)."""
    return 1007.0 + 0.1914 * (T - 300.0)


def pr_air(T):
    return np.interp(T, _T_ANCH, _PR_ANCH)


def k_air(T):
    """W/m/K, k = mu*cp/Pr (self consistent)."""
    return mu_air(T) * cp_air(T) / pr_air(T)


def rho_air(T, P=P_ATM):
    """kg/m^3, ideal gas law."""
    return P / (R_AIR * T)


def beta_air(T):
    """1/K, ideal-gas thermal expansion coefficient."""
    return 1.0 / T


def nu_air(T, P=P_ATM):
    """Kinematic viscosity, m^2/s."""
    return mu_air(T) / rho_air(T, P)


if __name__ == "__main__":
    for T in [275, 300, 400, 500, 600, 700, 800]:
        print(f"T={T:5.0f}K  rho={rho_air(T):.4f}  mu={mu_air(T):.3e}  "
              f"cp={cp_air(T):.1f}  k={k_air(T):.4f}  Pr={pr_air(T):.3f}  "
              f"beta={beta_air(T):.5f}")

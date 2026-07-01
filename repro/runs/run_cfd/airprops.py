"""
Air thermophysical properties for the RCCS calculation note.

Dry air at ~1 atm treated as an ideal gas. Property correlations from standard
sources (cited inline). All functions take absolute temperature T [K].

Sources:
  - Density: ideal gas, rho = P/(R*T), R_air = 287.05 J/kg-K.
  - Dynamic viscosity: Sutherland's law (White, "Viscous Fluid Flow", 3rd ed.,
    Table 1-2): mu = mu_ref (T/T_ref)^1.5 (T_ref+S)/(T+S),
    mu_ref = 1.716e-5 Pa.s at T_ref = 273.15 K, S = 110.4 K.
  - Thermal conductivity: Sutherland-form fit for air (White),
    k = k_ref (T/T_ref)^1.5 (T_ref+Sk)/(T+Sk),
    k_ref = 0.0241 W/m-K at 273.15 K, Sk = 194 K.
  - Specific heat cp(T): polynomial fit to dry-air data
    (Incropera & DeWitt, "Fundamentals of Heat and Mass Transfer", Table A.4),
    valid ~250-1050 K.

Validation vs Incropera Table A.4 at 300 K:
  rho=1.177, cp=1007, mu=1.846e-5, k=0.0263, Pr=0.707  (see __main__).
"""
import numpy as np

R_AIR = 287.05          # J/kg-K
P_DEFAULT = 101325.0    # Pa (input states ~1 atm; elevation ~180 m -> ~99 kPa; see note)


def rho(T, P=P_DEFAULT):
    return P / (R_AIR * T)


def mu(T):
    return 1.716e-5 * (T / 273.15) ** 1.5 * (273.15 + 110.4) / (T + 110.4)


def k(T):
    return 0.0241 * (T / 273.15) ** 1.5 * (273.15 + 194.0) / (T + 194.0)


def cp(T):
    # Polynomial fit to dry-air cp [J/kg-K], Incropera Table A.4 (250-1050 K)
    return (1.9327e-10 * T**4 - 7.9999e-7 * T**3 + 1.1407e-3 * T**2
            - 4.4890e-1 * T + 1.0575e3)


def Pr(T):
    return mu(T) * cp(T) / k(T)


def beta(T):
    return 1.0 / T           # ideal gas thermal expansion coefficient


def nu(T, P=P_DEFAULT):
    return mu(T) / rho(T, P)


def alpha(T, P=P_DEFAULT):
    return k(T) / (rho(T, P) * cp(T))


if __name__ == "__main__":
    for T in [250, 300, 350, 400, 500, 600, 800, 1000]:
        print(f"T={T:5d}K  rho={rho(T):.4f}  cp={cp(T):6.1f}  "
              f"mu={mu(T):.3e}  k={k(T):.4f}  Pr={Pr(T):.3f}")

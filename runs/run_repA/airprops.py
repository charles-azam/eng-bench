"""
Air properties at ~1 atm (101325 Pa), as functions of temperature.

Sources (general, standard references only -- NOT facility data):
  - Ideal-gas density:  rho = P/(R*T),  R_air = 287.05 J/kg-K
  - Dynamic viscosity:  Sutherland's law (White, "Viscous Fluid Flow")
        mu = mu0 * (T/T0)^1.5 * (T0+S)/(T+S),  mu0=1.716e-5, T0=273.15, S=110.4
  - Thermal conductivity: Sutherland-type fit (Lemmon & Jacobsen style /
        standard air-property tables), k0=0.02414, Tk0=273.15, Sk=194
  - Specific heat cp(T): low-order polynomial fit to standard air tables
        (Incropera & DeWitt, "Fundamentals of Heat and Mass Transfer", App. A)
  - Prandtl:  Pr = cp*mu/k
  - Thermal expansion (ideal gas): beta = 1/T
All temperatures in KELVIN unless a _C suffix is used.
"""
import numpy as np

P_ATM = 101325.0
R_AIR = 287.05

def rho(T):
    return P_ATM / (R_AIR * T)

def mu(T):
    mu0, T0, S = 1.716e-5, 273.15, 110.4
    return mu0 * (T / T0) ** 1.5 * (T0 + S) / (T + S)

def k(T):
    k0, T0, S = 0.02414, 273.15, 194.0
    return k0 * (T / T0) ** 1.5 * (T0 + S) / (T + S)

def cp(T):
    # cp [J/kg-K] fit valid ~250-1000 K, standard air tables
    Tc = T
    return 1005.0 + 0.0 * Tc + 3.3e-4 * (Tc - 300.0) ** 2 / 10.0 + 0.05 * (Tc - 300.0)

def cp_simple(T):
    # simpler, well-behaved cp fit (Incropera tables): rises slowly with T
    return 1006.0 + 0.05 * (T - 300.0) + 8e-5 * (T - 300.0) ** 2

def Pr(T):
    return cp_simple(T) * mu(T) / k(T)

def beta(T):
    return 1.0 / T

def nu(T):
    return mu(T) / rho(T)

def alpha(T):
    return k(T) / (rho(T) * cp_simple(T))

if __name__ == "__main__":
    for TC in [2, 20, 50, 100, 150, 300, 400]:
        T = TC + 273.15
        print(f"T={TC:4d}C  rho={rho(T):.4f}  mu={mu(T):.3e}  k={k(T):.4f}  "
              f"cp={cp_simple(T):.1f}  Pr={Pr(T):.4f}  nu={nu(T):.3e}")

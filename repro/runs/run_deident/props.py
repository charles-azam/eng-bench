"""
Air thermophysical properties at ~1 atm, from standard first-principles correlations.
Cited sources given in calculation_note.md. All temperatures in KELVIN unless noted.

Sources:
- Ideal-gas density: rho = P/(R T), R_air = 287.05 J/kg/K.
- Dynamic viscosity: Sutherland's law (White, Viscous Fluid Flow; NIST).
- Thermal conductivity: Sutherland-type law (Lemmon & Jacobsen 2004 fit form).
- c_p: polynomial fit to NIST/JANAF dry-air data over 250-1000 K.
- Pr = mu*cp/k ; beta = 1/T (ideal gas).
"""
import numpy as np

R_AIR = 287.05  # J/kg/K
P_ATM = 101325.0  # Pa (facility ~180 m elevation; use 1 atm, note ~-2% density if 99 kPa used)

def rho(T, P=P_ATM):
    """Density [kg/m3], ideal gas."""
    return P / (R_AIR * T)

def _clamp(T):
    # correlations valid ~200-1300 K; clamp to avoid extrapolation blow-ups
    return min(max(T, 200.0), 1300.0)

def mu(T):
    """Dynamic viscosity [Pa.s], Sutherland's law."""
    T = _clamp(T)
    mu0, T0, S = 1.716e-5, 273.15, 110.4
    return mu0 * (T / T0) ** 1.5 * (T0 + S) / (T + S)

def k(T):
    """Thermal conductivity [W/m/K], Sutherland-type law for air."""
    T = _clamp(T)
    k0, T0, Sk = 0.0241, 273.15, 194.0
    return k0 * (T / T0) ** 1.5 * (T0 + Sk) / (T + Sk)

def cp(T):
    """Specific heat [J/kg/K], polynomial fit to dry-air data 250-1000 K."""
    # Fit reproduces cp(300)=1005, cp(500)=1030, cp(800)=1099 J/kg/K
    t = _clamp(T) / 1000.0
    return 1000.0 * (1.0189 - 0.1378*t + 0.4021*t**2 - 0.1955*t**3)

def Pr(T):
    return mu(T) * cp(T) / k(T)

def beta(T):
    """Thermal expansion coeff [1/K], ideal gas."""
    return 1.0 / T

def nu(T, P=P_ATM):
    return mu(T) / rho(T, P)

if __name__ == "__main__":
    for Tc in [2, 20, 50, 100, 200, 300, 500]:
        T = Tc + 273.15
        print(f"T={Tc:4d}C  rho={rho(T):.4f}  mu={mu(T):.3e}  k={k(T):.4f}  "
              f"cp={cp(T):.1f}  Pr={Pr(T):.4f}")

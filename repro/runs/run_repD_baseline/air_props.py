"""
Air thermophysical properties.

Primary source: CoolProp (Bell et al., "Pure and Pseudo-pure Fluid
Thermophysical Property Evaluation and the Open-Source Thermophysical Property
Library CoolProp", Ind. Eng. Chem. Res. 53 (2014) 2498-2508), fluid "Air".

All properties evaluated at the local static pressure and the specified
temperature.  Site pressure taken as 99.0 kPa (facility near Chicago, ~180 m
elevation -> P ~ 101.325 * (1 - 2.25577e-5*180)^5.2559 ~ 99.2 kPa).

Density uses the ideal-gas value rho = P/(R T) with R = 287.05 J/kg/K, which
agrees with CoolProp to <0.3% over 250-800 K at ~1 atm and keeps beta = 1/T
consistent for the buoyancy integral.  cp, mu, k are taken from CoolProp.
"""
from CoolProp.CoolProp import PropsSI

P_SITE = 99000.0          # Pa, static pressure at the facility
R_AIR = 287.05            # J/kg/K


def rho(T, P=P_SITE):
    """Density [kg/m3] (ideal gas)."""
    return P / (R_AIR * T)


def mu(T, P=P_SITE):
    """Dynamic viscosity [Pa.s]."""
    return PropsSI("V", "T", T, "P", P, "Air")


def k(T, P=P_SITE):
    """Thermal conductivity [W/m/K]."""
    return PropsSI("L", "T", T, "P", P, "Air")


def cp(T, P=P_SITE):
    """Isobaric specific heat [J/kg/K]."""
    return PropsSI("C", "T", T, "P", P, "Air")


def Pr(T, P=P_SITE):
    """Prandtl number [-]."""
    return mu(T, P) * cp(T, P) / k(T, P)


def beta(T):
    """Thermal expansion coefficient [1/K] (ideal gas)."""
    return 1.0 / T


def nu(T, P=P_SITE):
    """Kinematic viscosity [m2/s]."""
    return mu(T, P) / rho(T, P)


def alpha(T, P=P_SITE):
    """Thermal diffusivity [m2/s]."""
    return k(T, P) / (rho(T, P) * cp(T, P))


if __name__ == "__main__":
    for Tc in (2, 20, 100, 200, 400, 600):
        T = Tc + 273.15
        print(f"T={Tc:4d} C  rho={rho(T):.3f}  mu={mu(T)*1e6:6.2f}e-6  "
              f"k={k(T):.4f}  cp={cp(T):.1f}  Pr={Pr(T):.3f}")

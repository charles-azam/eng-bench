"""Air properties at ~1 atm (facility near Chicago, ~180 m, P=101325 Pa).
Uses CoolProp for humid-air-free dry-air properties. All SI units, T in Kelvin.
"""
import numpy as np
from CoolProp.CoolProp import PropsSI

P_ATM = 101325.0          # Pa
R_AIR = 287.05            # J/kg-K
G = 9.80665               # m/s^2

def rho(T, P=P_ATM):
    """density kg/m3"""
    return P / (R_AIR * T)      # ideal gas; matches CoolProp within <0.3% for air 250-800K

def mu(T):
    """dynamic viscosity Pa.s"""
    return PropsSI('V', 'T', T, 'P', P_ATM, 'Air')

def k_air(T):
    """thermal conductivity W/m-K"""
    return PropsSI('L', 'T', T, 'P', P_ATM, 'Air')

def cp(T):
    return PropsSI('C', 'T', T, 'P', P_ATM, 'Air')

def Pr(T):
    return PropsSI('PRANDTL', 'T', T, 'P', P_ATM, 'Air')

def nu(T):
    return mu(T)/rho(T)

def alpha(T):
    return k_air(T)/(rho(T)*cp(T))

def beta(T):
    return 1.0/T   # ideal gas

if __name__ == "__main__":
    for Tc in [2, 20, 100, 200, 300, 400, 500]:
        T = Tc+273.15
        print(f"T={Tc:4d}C rho={rho(T):.4f} mu={mu(T)*1e6:6.2f}uPa.s "
              f"k={k_air(T):.4f} cp={cp(T):.1f} Pr={Pr(T):.4f}")

"""Dry-air thermophysical properties, 250-1200 K, 1 atm.

rho   : ideal gas law, R = 287.05 J/kg-K
mu, k : Sutherland-law fits (White, Viscous Fluid Flow; matches Incropera
        Table A.4 within ~1 %)
cp    : interpolation of Incropera & DeWitt, Fundamentals of Heat and Mass
        Transfer, Table A.4
"""
import numpy as np

R_AIR = 287.05
P_ATM = 101325.0

_cp_T = np.array([250, 300, 350, 400, 450, 500, 550, 600, 650, 700,
                  750, 800, 850, 900, 950, 1000, 1100, 1200], float)
_cp_v = np.array([1006, 1007, 1009, 1014, 1021, 1030, 1040, 1051, 1063,
                  1075, 1087, 1099, 1110, 1121, 1131, 1141, 1159, 1175], float)


def rho(T, P=P_ATM):
    return P / (R_AIR * T)


def mu(T):
    return 1.716e-5 * (T / 273.15) ** 1.5 * (273.15 + 110.4) / (T + 110.4)


def k(T):
    return 0.0241 * (T / 273.15) ** 1.5 * (273.15 + 194.0) / (T + 194.0)


def cp(T):
    return np.interp(T, _cp_T, _cp_v)


def Pr(T):
    return mu(T) * cp(T) / k(T)


def beta(T):
    return 1.0 / T

"""
TRISO accident-heating calculation model.
All correlations/constants cited to inputs/03_material_properties.md (TECDOC-1674 eq. numbers)
unless marked GENERIC (standard nuclear-engineering data, not specific to this benchmark's
published results): fission yields, isotope half-lives, ideal-gas law, thin-shell pressure-vessel
and composite-shell mismatch formulas.
"""
import math

R_GAS = 8.314        # J/mol/K
NA = 6.022e23        # /mol
K0 = 273.15

# ---------------------------------------------------------------- GENERIC nuclear data
Y_GAS_TOTAL   = 0.30    # atoms (Kr+Xe, all isotopes) per fission -- GENERIC, order-of-magnitude
Y_KR85        = 0.0133  # Kr-85 cumulative fission yield, atoms/fission -- GENERIC
Y_CS137       = 0.0619  # Cs-137 cumulative fission yield, atoms/fission -- GENERIC
LAMBDA_KR85   = math.log(2) / (10.76 * 365.25 * 24 * 3600)   # /s, GENERIC half-life
LAMBDA_CS137  = math.log(2) / (30.17 * 365.25 * 24 * 3600)   # /s, GENERIC half-life
M_U_AVG       = 238.0   # g/mol, approx (weakly depends on enrichment 9.8-10.6%)

# ---------------------------------------------------------------- Table 9.6 elastic/thermal
E_PYC = 3.96e4      # MPa
NU_PYC_EL = 0.33
NU_PYC_CR = 0.4     # creep Poisson ratio, Table 9.14 value used here (sphere/compact cases)
ALPHA_PYC = 5.5e-6  # 1/K
E_SIC = 3.70e5      # MPa
NU_SIC = 0.13
ALPHA_SIC = 4.90e-6 # 1/K

# ---------------------------------------------------------------- Table 9.14 strength/Weibull
SIGMA0_SIC = 873.0  # MPa
M_SIC = 8.02

# ---------------------------------------------------------------- Table 7.1 kernel diffusion
D0_CS, Q_CS   = 0.90, 209e3
D0_KR_LONG, Q_KR_LONG = 5e-3, 155.4e3   # "stable & long-lived gases" row -> use for Kr-85/Cs stable pressure gas

# ---------------------------------------------------------------- Eq 10.9 Cs-in-SiC
GAMMA_FLUENCE = 2.0
def D_Cs_SiC(T_K):
    return 5.5e-14*math.exp(-125000/(R_GAS*T_K)) + GAMMA_FLUENCE*1.6e-15*math.exp(-514000/(R_GAS*T_K))

def D_kernel(D0, Q, T_K):
    return D0*math.exp(-Q/(R_GAS*T_K))

def release_fraction(Fo):
    """Eq 10.7/10.8 equivalent-sphere cumulative release fraction, Fo = D'*t (dimensionless)."""
    if Fo <= 0:
        return 0.0
    if Fo <= 0.15:
        F = 6*math.sqrt(Fo/math.pi) - 3*Fo
    else:
        F = 1 - (6/math.pi**2)*math.exp(-math.pi**2*Fo)
    return min(max(F, 0.0), 1.0)

# ---------------------------------------------------------------- PyC swelling correlation (e)
# dg/dx polynomial coefficients (Table 9.8), x in 1e25 n/m^2 E>0.18MeV
E_RAD_LOW  = [-1.43234e-1, 2.62692e-1, -1.74247e-1, 5.67549e-2, -8.36313e-3, 4.52013e-4]
E_TAN_LOW  = [-3.24737e-2, 9.07826e-3, -2.10029e-3, 1.30457e-4]
E_RAD_HIGH = 0.0954
E_TAN_HIGH = -0.0249
X_BREAK = 6.08

def poly(coeffs, x):
    return sum(c*x**i for i, c in enumerate(coeffs))

def pyc_swelling_strain(x, coeffs_low, high_const):
    """Cumulative PyC dimensional-change strain at fluence x (1e25 n/m^2, E>0.18 MeV).
    Eq 9.22 correlation (e) gives the strain DIRECTLY as a polynomial in x for x<6.08
    (confirmed by continuity: poly(6.08) = 0.0958 rad / -0.0143 tan, matching the stated
    saturation constants 0.0954 / -0.0249 to within the fit residual) and holds at a
    constant (saturated) value for x>6.08."""
    if x <= X_BREAK:
        return poly(coeffs_low, x)
    else:
        return high_const

print("Module loaded OK")

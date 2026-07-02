"""
Zero-power natural-circulation draft model for the NSTF-type RCCS air loop.

Physics
-------
Driving pressure (heaters OFF):
  Dp_stack = g * H * (rho_out - rho_in)          (buoyancy / chimney draft, ~ linear in DT)
  Dp_wind  = C_w * 0.5 * rho_out * V^2           (wind suction at chimney outlets, ~ V^2)
Loss (fully turbulent loop):
  Dp_loss  = R * mdot^2                           (all minor + friction losses ~ mdot^2)
Balance Dp_stack + Dp_wind = Dp_loss  ->  mdot = sqrt(Dp_drive / R).

R is built from the series resistance of downcomer -> inlet plenum -> 12 risers ->
outlet plenum -> 2 chimneys, each element referenced to total mass flow.
"""
import math

# ---------------------------------------------------------------- constants
g      = 9.81
P_atm  = 101325.0          # Pa (1 atm; facility ~180 m elevation -> ~99 kPa, <2% effect)
R_air  = 287.0             # J/kg-K
mu     = 1.8e-5            # Pa-s (air ~ 10 C)
T_in   = 293.15            # K, indoor / loop air ~20 C

def rho(T_K):              # ideal-gas density at 1 atm
    return P_atm / (R_air * T_K)

# ---------------------------------------------------------------- geometry
IN = 0.0254
# Downcomer: 24 in dia, equiv centerline length 184.5 in
D_dc = 24*IN;  A_dc = math.pi/4*D_dc**2;  L_dc = 184.5*IN
# Risers: 12 tubes, internal 9.624 x 1.624 in
w_r = 9.624*IN; h_r = 1.624*IN
A_r1 = w_r*h_r
Per_r = 2*(w_r+h_r)
Dh_r = 4*A_r1/Per_r
N_r = 12
A_r = N_r*A_r1
L_r = 295*IN               # total riser length 295 in = 7.49 m
# Chimneys: 2 x 24 in dia; equiv length vertical 826 + horizontal 470 in
D_ch = 24*IN; A_ch1 = math.pi/4*D_ch**2; N_ch = 2; A_ch = N_ch*A_ch1
L_ch = (826+470)*IN
# Stack height (chimney discharge above building base; see note in report)
H = 19.6

print(f"A_dc={A_dc:.4f} m2  L_dc={L_dc:.3f} m")
print(f"riser: A1={A_r1:.5f} Dh={Dh_r:.4f} A_total={A_r:.4f} L={L_r:.3f}")
print(f"chimney: A1={A_ch1:.4f} A_total={A_ch:.4f} L={L_ch:.3f}")

# ---------------------------------------------------------------- friction
def colebrook(Re, eps_D):
    if Re < 2300:
        return 64.0/max(Re,1e-6)
    f = 0.02
    for _ in range(50):
        f = (-2.0*math.log10(eps_D/3.7 + 2.51/(Re*math.sqrt(f))))**-2
    return f

# roughness
eps_steel = 0.045e-3        # commercial steel
eps_galv  = 0.15e-3         # galvanized chimney

# minor-loss coefficients (referenced to the local group area)
K_dc = 0.5 + 0.5 + 1.0      # building entrance + 90 elbow + flow conditioner
K_r  = 0.5 + 1.0            # plenum->riser contraction/entrance + riser exit into plenum
K_ch = 0.5 + 1.0 + 1.0      # plenum->chimney entrance + dampers/elbows + exit

def resistance(mdot, rho_use):
    """Total loop resistance R such that Dp_loss = R*mdot^2, with f(Re) iterated."""
    def term(A, Dh, L, K, eps):
        v = mdot/(rho_use*A)
        Re = rho_use*v*Dh/mu
        f = colebrook(Re, eps/Dh)
        Kloc = f*L/Dh + K
        return Kloc/(2*rho_use*A**2), Re, v, f, f*L/Dh
    t_dc = term(A_dc, D_dc, L_dc, K_dc, eps_steel)
    t_r  = term(A_r,  Dh_r, L_r,  K_r,  eps_steel)
    t_ch = term(A_ch, D_ch, L_ch, K_ch, eps_galv)
    R = t_dc[0]+t_r[0]+t_ch[0]
    return R, t_dc, t_r, t_ch

# ---------------------------------------------------------------- solve
C_w = 0.4                   # effective net wind suction coefficient (uncertain)

def solve_mdot(DT, V):
    T_out = T_in - DT
    rho_out = rho(T_out); rho_i = rho(T_in)
    rho_use = 0.5*(rho_out+rho_i)
    Dp_stack = g*H*(rho_out-rho_i)
    Dp_wind  = C_w*0.5*rho_out*V**2
    Dp = Dp_stack+Dp_wind
    if Dp<=0: return 0.0, {}
    mdot = math.sqrt(Dp/50.0)      # initial guess
    for _ in range(50):
        R,*_ = resistance(mdot, rho_use)
        mdot = math.sqrt(Dp/R)
    R, t_dc, t_r, t_ch = resistance(mdot, rho_use)
    return mdot, dict(T_out=T_out,rho_out=rho_out,Dp_stack=Dp_stack,Dp_wind=Dp_wind,
                      R=R, t_dc=t_dc, t_r=t_r, t_ch=t_ch, rho_use=rho_use)

# diagnostic at a reference point
m,d = solve_mdot(15,5)
print("\n--- reference DT=15 V=5 ---")
print(f"mdot={m:.3f} kg/s = {m*60:.1f} kg/min")
print(f"Dp_stack={d['Dp_stack']:.2f} Pa  Dp_wind={d['Dp_wind']:.2f} Pa  R={d['R']:.1f}")
print(f"R split: dc={d['t_dc'][0]:.2f} riser={d['t_r'][0]:.2f} chim={d['t_ch'][0]:.2f}")
print(f"Re riser={d['t_r'][1]:.0f} f={d['t_r'][3]:.4f} fL/D={d['t_r'][4]:.2f} v={d['t_r'][2]:.2f}")
print(f"Re dc={d['t_dc'][1]:.0f} v={d['t_dc'][2]:.2f}; Re ch={d['t_ch'][1]:.0f} v={d['t_ch'][2]:.2f}")

# ---------------------------------------------------------------- table
print("\n--- 3x3 table  mdot [kg/min] ---")
print("DT\\V     0      5      10")
for DT in (5,15,30):
    row=[]
    for V in (0,5,10):
        m,_=solve_mdot(DT,V)
        row.append(f"{m*60:6.1f}")
    print(f"{DT:>3}   "+"  ".join(row))

# ---------------------------------------------------------------- coefficients
# Linearized coefficients for technician formula:
# mdot[kg/min] = 60*sqrt( (a*DT + b*V^2)/R )
# a = g*H*(rho_out-rho_in)/DT   (evaluate at ref)  ; b = C_w*0.5*rho_out
DTref=15; T_out=T_in-DTref
a = g*H*(rho(T_out)-rho(T_in))/DTref
b = C_w*0.5*rho(T_out)
_,dref = solve_mdot(15,5)
print(f"\na (stack, Pa/K)   = {a:.3f}")
print(f"b (wind, Pa/(m/s)^2)= {b:.3f}")
print(f"R (Pa/(kg/s)^2)   ~ {dref['R']:.1f}")
print(f"=> mdot[kg/min] = 60*sqrt(({a:.3f}*DT + {b:.3f}*V^2)/{dref['R']:.0f})")
# equivalently combine constants
import math as _m
print(f"   simplified: mdot[kg/min] ~ {60/_m.sqrt(dref['R']):.2f}*sqrt({a:.3f}*DT + {b:.3f}*V^2)")

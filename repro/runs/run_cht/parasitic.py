"""Independent estimate of parasitic (structural) heat loss to justify Q_air ~ 56 kW
for 82 kWe electric input. All from insulation conduction + external convection/radiation."""
import numpy as np
sig=5.67e-8
def loss(name, T_hot_C, k, thk, A, T_amb_C=20, h_out=8, eps_out=0.8):
    # series: insulation conduction + outer surface (conv+rad linearized)
    Th=T_hot_C+273.15; Ta=T_amb_C+273.15
    # iterate outer surface temp
    Ts=0.5*(Th+Ta)
    for _ in range(50):
        R_ins=thk/k
        q_ins=(Th-Ts)/R_ins
        hr=eps_out*sig*(Ts**2+Ta**2)*(Ts+Ta)
        q_out=(h_out+hr)*(Ts-Ta)
        Ts+=0.2*(q_ins-q_out)/max(q_ins,q_out,1)  # relax
        Ts=Th-q_ins*R_ins if False else Ts
    # solve properly: q_ins=q_out
    from scipy.optimize import brentq
    f=lambda Ts:(Th-Ts)/(thk/k)-(h_out+eps_out*sig*(Ts**2+Ta**2)*(Ts+Ta))*(Ts-Ta)
    Ts=brentq(f,Ta,Th)
    q=(Th-Ts)/(thk/k)
    print(f"{name:32s}: q={q:6.1f} W/m2  A={A:5.2f} m2 -> {q*A/1e3:5.2f} kW (Ts={Ts-273.15:.0f}C)")
    return q*A
tot=0
# Behind heaters: heater backing ~ plate temp+; through 2in Duraboard k~0.10@~400C
tot+=loss("Back of heaters (Duraboard 2in)", 400, 0.10, 0.0508, 10.18)
# N/S/W cavity walls: 6in SuperIsol, inner ~ cavity gas ~230C
tot+=loss("N/S/W cavity walls (SuperIsol 6in)", 230, 0.08, 0.152, 18.3)
# uninsulated outlet plenum (hot air ~117C, aluminum) - conduction negligible, ~air film
tot+=loss("Outlet plenum shell (uninsulated)", 117, 200, 0.003, 10.0)  # aluminium, film-limited
print(f"TOTAL parasitic estimate ~ {tot/1e3:.1f} kW  (of 82 kWe -> Q_air ~ {82-tot/1e3:.0f} kW)")

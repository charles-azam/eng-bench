# CFD cross-check results (buoyantSimpleFoam + viewFactor surface radiation)

Case: 2-D vertical cavity slice, depth 0.7066 m (plate face -> riser front plane),
height 2.0 m (representative segment; per-area radiative exchange between two
parallel strips is height-independent in the parallel-plate limit), 1-cell-thick
(2-D). Air modelled as transparent (non-participating); surface-to-surface
radiation by view factors (viewFactorsGen). Laminar buoyant flow, gravity -y.

Boundary temperatures FIXED at the 1-D model's predictions:
  plate (mock RPV)  T = 663.15 K (390 C), emissivity 0.785
  riser front plane T = 433.15 K (160 C), emissivity 0.80
  top/bottom        adiabatic, reradiating (emissivity 1.0)

RESULT (latest time, ~steady):
  Plate total wall heat flux (conv+rad), area-mean : 6215 W/m^2  (min 5975, max 6285)
  Plate radiative flux (qr), area-mean             : 5960 W/m^2  (95.9 % of total)
  Plate convective flux                            :  255 W/m^2  ( 4.1 %)
  Riser total wall flux (absorbed)                 : 4726 W/m^2
  Riser radiative flux (qr)                        : 4596 W/m^2

RECONCILIATION with 1-D network model:
  Required plate flux for 56 kW / 8.84 m^2   = 6335 W/m^2
  CFD plate flux at T_plate = 390 C          = 6215 W/m^2   (-1.9 %)
  => the plate temperature that removes exactly 56 kW is ~391-392 C in the CFD,
     vs 390 C from the 1-D model: agreement within ~2 C / 2 %.
  Radiative fraction: CFD 96 % vs 1-D network 93 % -- both confirm radiation
     is the dominant (>90 %) heat-transfer mode across the cavity.

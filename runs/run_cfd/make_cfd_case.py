#!/usr/bin/env python3
"""
Generate the OpenFOAM buoyantSimpleFoam + viewFactor (surface-to-surface)
radiation case for the RCCS cavity cross-check.

2-D vertical slice of the cavity:
  x = depth  (plate at x=0 ; riser front plane at x=CAV_DEPTH)
  y = height (0 .. H_PLATE)
  z = 1-cell thickness (empty patches)  -> per-metre-of-width slice

Boundary temperatures fixed at the 1-D model's predicted values; the CFD then
independently predicts the plate<->riser heat flux and its radiative fraction.
If plate=390 C / riser=160 C reproduces ~6.3 kW/m2 (=56 kW / 8.84 m2) with ~90%
radiative, the 1-D heated-wall temperature is corroborated.
"""
import os

CAV_DEPTH = 0.7066
H = 2.00
THK = 0.10
NX, NY = 24, 80
T_PLATE = 663.15      # 390 C  (1-D prediction)
T_RISER = 433.15      # 160 C  (1-D riser front-face)
EPS_PLATE = 0.785
EPS_RISER = 0.80

CASE = "cfd"
def w(path, content):
    full = os.path.join(CASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content)

HDR = """/*--------------------------------*- C++ -*----------------------------------*/
FoamFile
{{ version 2.0; format ascii; class {cls}; object {obj}; }}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""

# ---------------- blockMeshDict ----------------
w("system/blockMeshDict", HDR.format(cls="dictionary", obj="blockMeshDict") + f"""
scale 1;
vertices
(
    (0        0    0)
    ({CAV_DEPTH} 0    0)
    ({CAV_DEPTH} {H} 0)
    (0        {H}  0)
    (0        0    {THK})
    ({CAV_DEPTH} 0    {THK})
    ({CAV_DEPTH} {H} {THK})
    (0        {H}  {THK})
);
blocks ( hex (0 1 2 3 4 5 6 7) ({NX} {NY} 1) simpleGrading (1 1 1) );
edges ();
boundary
(
    plate
    {{ type wall; inGroups (viewFactorWall); faces ( (0 4 7 3) ); }}
    riser
    {{ type wall; inGroups (viewFactorWall); faces ( (1 2 6 5) ); }}
    adiabatic
    {{ type wall; inGroups (viewFactorWall); faces ( (0 1 5 4) (3 7 6 2) ); }}
    frontBack
    {{ type empty; faces ( (0 3 2 1) (4 5 6 7) ); }}
);
mergePatchPairs ();
""")

# ---------------- constant ----------------
w("constant/g", HDR.format(cls="uniformDimensionedVectorField", obj="g") +
  "\ndimensions [0 1 -2 0 0 0 0];\nvalue (0 -9.80665 0);\n")

w("constant/thermophysicalProperties", HDR.format(cls="dictionary", obj="thermophysicalProperties") + """
thermoType
{
    type            heRhoThermo;
    mixture         pureMixture;
    transport       const;
    thermo          hConst;
    equationOfState perfectGas;
    specie          specie;
    energy          sensibleEnthalpy;
}
pRef 101325;
mixture
{
    specie          { molWeight 28.96; }
    thermodynamics  { Cp 1005; Hf 0; }
    transport       { mu 1.85e-05; Pr 0.71; }
}
""")

w("constant/turbulenceProperties", HDR.format(cls="dictionary", obj="turbulenceProperties") +
  "\nsimulationType laminar;\n")

w("constant/radiationProperties", HDR.format(cls="dictionary", obj="radiationProperties") + """
radiation on;
radiationModel viewFactor;
viewFactorCoeffs
{
    smoothing true;
    constantEmissivity true;
}
solverFreq 5;
absorptionEmissionModel none;
scatterModel none;
sootModel none;
""")

w("constant/boundaryRadiationProperties", HDR.format(cls="dictionary", obj="boundaryRadiationProperties") + f"""
plate     {{ type lookup; emissivity {EPS_PLATE}; absorptivity {EPS_PLATE}; }}
riser     {{ type lookup; emissivity {EPS_RISER}; absorptivity {EPS_RISER}; }}
adiabatic {{ type lookup; emissivity 1.0; absorptivity 1.0; }}
""")

w("constant/viewFactorsDict", HDR.format(cls="dictionary", obj="viewFactorsDict") + """
writeViewFactorMatrix   true;
writePatchViewFactors   false;
writeFacesAgglomeration true;
patchAgglomeration
{
    viewFactorWall
    {
        nFacesInCoarsestLevel 20;
        featureAngle          10;
    }
}
maxDynListLength 200000;
""")

# ---------------- 0/ fields ----------------
w("0/T", HDR.format(cls="volScalarField", obj="T") + f"""
dimensions [0 0 0 1 0 0 0];
internalField uniform 500;
boundaryField
{{
    plate     {{ type fixedValue; value uniform {T_PLATE}; }}
    riser     {{ type fixedValue; value uniform {T_RISER}; }}
    adiabatic {{ type zeroGradient; }}
    frontBack {{ type empty; }}
}}
""")

w("0/U", HDR.format(cls="volVectorField", obj="U") + """
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 0);
boundaryField
{
    plate     { type noSlip; }
    riser     { type noSlip; }
    adiabatic { type noSlip; }
    frontBack { type empty; }
}
""")

w("0/p_rgh", HDR.format(cls="volScalarField", obj="p_rgh") + """
dimensions [1 -1 -2 0 0 0 0];
internalField uniform 101325;
boundaryField
{
    plate     { type fixedFluxPressure; value uniform 101325; }
    riser     { type fixedFluxPressure; value uniform 101325; }
    adiabatic { type fixedFluxPressure; value uniform 101325; }
    frontBack { type empty; }
}
""")

w("0/p", HDR.format(cls="volScalarField", obj="p") + """
dimensions [1 -1 -2 0 0 0 0];
internalField uniform 101325;
boundaryField
{
    plate     { type calculated; value uniform 101325; }
    riser     { type calculated; value uniform 101325; }
    adiabatic { type calculated; value uniform 101325; }
    frontBack { type empty; }
}
""")

w("0/qr", HDR.format(cls="volScalarField", obj="qr") + """
dimensions [1 0 -3 0 0 0 0];
internalField uniform 0;
boundaryField
{
    plate     { type greyDiffusiveRadiationViewFactor; qro uniform 0; value uniform 0; }
    riser     { type greyDiffusiveRadiationViewFactor; qro uniform 0; value uniform 0; }
    adiabatic { type greyDiffusiveRadiationViewFactor; qro uniform 0; value uniform 0; }
    frontBack { type empty; }
}
""")

# ---------------- system ----------------
w("system/controlDict", HDR.format(cls="dictionary", obj="controlDict") + """
application     buoyantSimpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         2000;
deltaT          1;
writeControl    timeStep;
writeInterval   500;
purgeWrite      2;
writeFormat     ascii;
writePrecision  7;
writeCompression off;
timeFormat      general;
runTimeModifiable true;
functions
{
    wallHeatFlux
    {
        type            wallHeatFlux;
        libs            (fieldFunctionObjects);
        patches         (plate riser);
        qr              qr;
        writeControl    writeTime;
    }
}
""")

w("system/fvSchemes", HDR.format(cls="dictionary", obj="fvSchemes") + """
ddtSchemes      { default steadyState; }
gradSchemes     { default Gauss linear; }
divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss upwind;
    div(phi,h)      bounded Gauss upwind;
    div(phi,K)      bounded Gauss upwind;
    div(phi,k)      bounded Gauss upwind;
    div(phi,epsilon) bounded Gauss upwind;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes   { default corrected; }
""")

w("system/fvSolution", HDR.format(cls="dictionary", obj="fvSolution") + """
solvers
{
    p_rgh
    {
        solver          GAMG;
        smoother        DICGaussSeidel;
        tolerance       1e-8;
        relTol          0.01;
    }
    "(U|h|k|epsilon)"
    {
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-8;
        relTol          0.1;
    }
    G
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-4;
        relTol          0.1;
    }
}
SIMPLE
{
    momentumPredictor yes;
    nNonOrthogonalCorrectors 0;
    pRefCell        0;
    pRefValue       101325;
    rhoMin          0.3;
    rhoMax          1.5;
    residualControl
    {
        p_rgh           1e-4;
        U               1e-4;
        h               1e-4;
    }
}
relaxationFactors
{
    fields { rho 1.0; p_rgh 0.7; }
    equations { U 0.3; h 0.3; "(k|epsilon)" 0.5; }
}
""")

print("CFD case written to", CASE)

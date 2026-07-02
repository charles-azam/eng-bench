import os
HDR='''FoamFile { version 2.0; format ascii; class volScalarField; object %s; }
'''
def vol(cls,obj): return f"FoamFile {{ version 2.0; format ascii; class {cls}; object {obj}; }}\n"

def write(obj, dims, internal, patches, cls='volScalarField'):
    s=vol(cls,obj)
    s+=f"dimensions {dims};\ninternalField uniform {internal};\nboundaryField\n{{\n"
    for name,body in patches.items():
        s+=f"    {name}\n    {{\n"
        for k,v in body.items():
            s+=f"        {k} {v};\n"
        s+="    }\n"
    s+="}\n"
    open(f"0.orig/{obj}","w").write(s)

WALLS=['plate','riser','topAndBottom']
EMPTY={'frontAndBack':{'type':'empty'}}

# U
p={n:{'type':'noSlip'} for n in WALLS}; p.update(EMPTY)
write('U','[0 1 -1 0 0 0 0]','(0 0 0)',p,'volVectorField')
# p
p={n:{'type':'calculated','value':'$internalField'} for n in WALLS}; p.update(EMPTY)
write('p','[1 -1 -2 0 0 0 0]','1e5',p)
# p_rgh
p={n:{'type':'fixedFluxPressure','value':'uniform 1e5'} for n in WALLS}; p.update(EMPTY)
write('p_rgh','[1 -1 -2 0 0 0 0]','1e5',p)
# k
p={n:{'type':'kqRWallFunction','value':'uniform 3.75e-4'} for n in WALLS}; p.update(EMPTY)
write('k','[0 2 -2 0 0 0 0]','3.75e-4',p)
# omega
p={n:{'type':'omegaWallFunction','value':'uniform 0.12'} for n in WALLS}; p.update(EMPTY)
write('omega','[0 0 -1 0 0 0 0]','0.12',p)
# nut
p={n:{'type':'nutUWallFunction','value':'uniform 0'} for n in WALLS}; p.update(EMPTY)
write('nut','[0 2 -1 0 0 0 0]','0',p)
# alphat
p={n:{'type':'compressible::alphatWallFunction','Prt':'0.85','value':'uniform 0'} for n in WALLS}; p.update(EMPTY)
write('alphat','[1 -1 -1 0 0 0 0]','0',p)

# T : plate = fixed electric flux (T solved); riser = convective sink (T solved); both radiate
pT={}
pT['plate']={'type':'externalWallHeatFluxTemperature','mode':'flux',
             'q':'uniform 5501','qr':'qr','qrRelaxation':'0.2','kappaMethod':'fluidThermo','value':'uniform 600'}
pT['riser']={'type':'externalWallHeatFluxTemperature','mode':'coefficient',
             'h':'uniform 82.3','Ta':'uniform 341.85','qr':'qr','qrRelaxation':'0.2','kappaMethod':'fluidThermo',
             'value':'uniform 400'}
pT['topAndBottom']={'type':'zeroGradient'}   # adiabatic, re-radiating
pT.update(EMPTY)
write('T','[0 0 0 1 0 0 0]','320',pT)

# G  (fvDOM incident radiation)
pG={n:{'type':'MarshakRadiation','emissivityMode':'lookup','value':'uniform 0'} for n in WALLS}
pG.update(EMPTY)
write('G','[1 0 -3 0 0 0 0]','0',pG)
# IDefault
pI={n:{'type':'greyDiffusiveRadiation','value':'uniform 0'} for n in WALLS}
pI.update(EMPTY)
write('IDefault','[1 0 -3 0 0 0 0]','0',pI)
print("fields written:", sorted(os.listdir('0.orig')))

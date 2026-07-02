import re, numpy as np, os
Ldir=sorted([d for d in os.listdir('.') if d.isdigit()],key=int)[-1]
txt=open(f"{Ldir}/T").read()
def patch_list(name):
    # find the patch block, then nonuniform List<scalar> N ( ... )
    m=re.search(name+r"\s*\{.*?value\s+nonuniform List<scalar>\s*\d+\s*\((.*?)\)",txt,re.S)
    if not m:  # fixedValue uniform fallback
        return None
    return np.array([float(x) for x in m.group(1).split()])
plate=patch_list("plate"); riser=patch_list("riser")
H=6.7; 
print("time dir",Ldir)
if plate is not None:
    z=np.linspace(H/len(plate)/2, H-H/len(plate)/2, len(plate))
    np.savetxt("plate_profile.dat",np.c_[z,plate-273.15])
    np.savetxt("riser_profile.dat",np.c_[z,riser-273.15])
    print(f"plate T: bottom {plate[0]-273.15:.0f}C mid {plate[len(plate)//2]-273.15:.0f}C top {plate[-1]-273.15:.0f}C mean {plate.mean()-273.15:.0f}C")
    print(f"riser T: bottom {riser[0]-273.15:.0f}C mid {riser[len(riser)//2]-273.15:.0f}C top {riser[-1]-273.15:.0f}C mean {riser.mean()-273.15:.0f}C")
    # value at z=3500mm
    i=np.argmin(abs(z-3.5))
    print(f"@ z=3500mm: plate={plate[i]-273.15:.0f}C  riser={riser[i]-273.15:.0f}C")

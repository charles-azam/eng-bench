import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
p=np.loadtxt("plate_profile.dat"); r=np.loadtxt("riser_profile.dat")
fig,ax=plt.subplots(figsize=(6,5))
ax.plot(p[:,1],p[:,0],'r-',lw=2,label="CFD plate (heated wall)")
ax.plot(r[:,1],r[:,0],'b-',lw=2,label="CFD riser wall")
# reduced-model points at z=3.5m
ax.plot(372,3.5,'r^',ms=12,label="reduced plate (lumped) 372C")
ax.plot(131,3.5,'bs',ms=10,label="reduced riser mean 131C")
ax.plot(181,3.5,'bD',ms=9,mfc='none',label="reduced riser front-face 181C")
ax.axhline(3.5,color='gray',ls=':',lw=1)
ax.set_xlabel("wall temperature (C)"); ax.set_ylabel("height z (m)")
ax.set_title("CFD wall temperatures vs reduced model (Case 1, 56 kW)\nheat flux prescribed, T solved, fvDOM radiation")
ax.legend(fontsize=8,loc='upper right'); ax.grid(alpha=.3)
plt.tight_layout(); plt.savefig("../../figs/cfd_profiles.png",dpi=120)
print("saved figs/cfd_profiles.png")

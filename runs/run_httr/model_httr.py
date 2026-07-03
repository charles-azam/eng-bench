"""
HTTR average fuel lattice — TRISO double-heterogeneity pin-in-block cell for OpenMC.

Purpose: compute k_inf(T) at isothermal temperatures to derive the isothermal
temperature (reactivity) coefficient alpha(T) of the HTTR core.

Design data sources (see output/sources.md): IAEA/JAERI HTTR fabrication paper
(TRISO layers), INL deterministic-modeling benchmark compilation (geometry,
enrichment zoning, graphite grades/impurities), JAEA HTTR outline.

Geometry modeled: Wigner-Seitz cylindrical pin cell (white radial boundary,
reflective top/bottom) preserving the block's graphite-to-fuel volume ratio,
with explicit randomly-packed TRISO particles in the annular fuel compact.
BOL (fresh) fuel, core-average enrichment. This isolates the local
spectral + Doppler feedback that governs the LOFC transient.
"""
import argparse
import numpy as np
import openmc

def build(temp=294.0, enrich=6.0, packing=0.30, sab='c_Graphite', seed=1,
          bp=True):
    """bp=True smears the block's burnable-poison boron into the block graphite.
    Core-average BP: 2 rods/block, r=0.7 cm, L=50 cm, rho~1.8 g/cc B4C/C, 2.25 wt% nat-B,
    smeared over the block-matrix graphite volume of this Wigner-Seitz cell."""
    # ---------------- Materials ----------------
    # UO2 kernel
    uo2 = openmc.Material(name='UO2 kernel')
    uo2.add_element('U', 1.0, enrichment=enrich)
    uo2.add_element('O', 2.0)
    uo2.set_density('g/cm3', 10.41)  # HTTR UO2 kernel design density (95% TD, INL)
    uo2.add_s_alpha_beta('c_U_in_UO2')
    uo2.add_s_alpha_beta('c_O_in_UO2')
    uo2.temperature = temp

    buff = openmc.Material(name='buffer PyC')
    buff.add_element('C', 1.0)
    buff.set_density('g/cm3', 1.10)
    buff.add_s_alpha_beta(sab)
    buff.temperature = temp

    ipyc = openmc.Material(name='IPyC')
    ipyc.add_element('C', 1.0)
    ipyc.set_density('g/cm3', 1.85)
    ipyc.add_s_alpha_beta(sab)
    ipyc.temperature = temp

    sic = openmc.Material(name='SiC')
    sic.add_element('Si', 1.0)
    sic.add_element('C', 1.0)
    sic.set_density('g/cm3', 3.20)
    sic.add_s_alpha_beta('c_Si_in_SiC')
    sic.add_s_alpha_beta('c_C_in_SiC')
    sic.temperature = temp

    opyc = openmc.Material(name='OPyC')
    opyc.add_element('C', 1.0)
    opyc.set_density('g/cm3', 1.85)
    opyc.add_s_alpha_beta(sab)
    opyc.temperature = temp

    # Graphite matrix of the fuel compact (with small natural-boron impurity)
    # IG-110 / matrix graphite ~1.70 g/cc, boron-equiv impurity ~0.8 ppm by wt.
    def graphite(name, density, boron_ppm, extra_natB_ao=0.0):
        # boron_ppm: natural-B impurity by weight (ppm). extra_natB_ao: additional
        # natural-B as atom fraction relative to C (used for smeared burnable poison).
        m = openmc.Material(name=name)
        m.add_element('C', 1.0)
        natB_ao = boron_ppm * 1e-6 * (12.011 / 10.811) + extra_natB_ao
        if natB_ao > 0:
            m.add_element('B', natB_ao, percent_type='ao')
        m.set_density('g/cm3', density)
        m.add_s_alpha_beta(sab)
        m.temperature = temp
        return m

    # Smeared burnable-poison natural-B atom fraction in the block graphite (BOL).
    # 2 rods/block x pi*0.7^2*50 cm3 x 1.8 g/cc x 2.25 wt% natB -> 6.24 g natB/block;
    # core-avg 5.34e18 natB/cm3; concentrated into block-graphite region (61.2% of WS cell)
    # -> 8.72e18 natB/cm3 in block graphite; /8.77e22 C/cm3 = 9.94e-5 ao.
    bp_ao = 9.94e-5 if bp else 0.0
    matrix = graphite('compact matrix graphite', 1.70, 0.8)
    sleeve = graphite('fuel sleeve graphite (IG-110)', 1.77, 0.8)
    block  = graphite('fuel block graphite (IG-110)', 1.75, 0.8, extra_natB_ao=bp_ao)

    helium = openmc.Material(name='helium coolant')
    helium.add_element('He', 1.0)
    helium.set_density('g/cm3', 0.00490)  # He at ~4 MPa, ~700 K (approx; negligible neutronic worth)
    helium.temperature = temp

    # ---------------- TRISO particle universe ----------------
    r_kernel = 0.0300   # 300 um (600 um dia)
    r_buff   = r_kernel + 0.0060  # 60 um
    r_ipyc   = r_buff   + 0.0030  # 30 um
    r_sic    = r_ipyc   + 0.0025  # 25 um
    r_opyc   = r_sic    + 0.0045  # 45 um  -> particle radius 0.0460 cm

    s_k = openmc.Sphere(r=r_kernel)
    s_b = openmc.Sphere(r=r_buff)
    s_i = openmc.Sphere(r=r_ipyc)
    s_s = openmc.Sphere(r=r_sic)
    s_o = openmc.Sphere(r=r_opyc)
    c_k = openmc.Cell(fill=uo2, region=-s_k)
    c_b = openmc.Cell(fill=buff, region=+s_k & -s_b)
    c_i = openmc.Cell(fill=ipyc, region=+s_b & -s_i)
    c_s = openmc.Cell(fill=sic, region=+s_i & -s_s)
    c_o = openmc.Cell(fill=opyc, region=+s_s & -s_o)
    c_m = openmc.Cell(fill=matrix, region=+s_o)
    triso_univ = openmc.Universe(cells=[c_k, c_b, c_i, c_s, c_o, c_m])

    # ---------------- Pin cell geometry ----------------
    H = 3.9                    # axial height = 1 compact (cm)
    r_hole   = 0.5             # compact inner hole radius (ID 10 mm) -> helium
    r_compact= 1.3             # compact OD 26 mm
    r_sleeve = 1.7             # fuel rod / sleeve OD 34 mm
    r_channel= 2.05            # coolant channel bore dia 41 mm
    # equal-area cell radius: block area / rods per block
    block_af = 36.0            # across flats (cm)
    block_area = (np.sqrt(3)/2) * block_af**2
    n_rods = 33.0
    r_cell = np.sqrt(block_area / n_rods / np.pi)   # ~3.29 cm

    z0 = openmc.ZPlane(z0=0.0, boundary_type='reflective')
    z1 = openmc.ZPlane(z0=H,  boundary_type='reflective')
    cyl_hole   = openmc.ZCylinder(r=r_hole)
    cyl_comp   = openmc.ZCylinder(r=r_compact)
    cyl_sleeve = openmc.ZCylinder(r=r_sleeve)
    cyl_chan   = openmc.ZCylinder(r=r_channel)
    cyl_cell   = openmc.ZCylinder(r=r_cell, boundary_type='white')

    zslab = +z0 & -z1

    # Fill compact annulus with packed TRISO
    compact_region = +cyl_hole & -cyl_comp & zslab
    # pack over the full solid cylinder (a supported container); the annular
    # compact cell realizes only the annulus, so annular fuel loading = pf * V_annulus.
    packing_region = -cyl_comp & +z0 & -z1
    centers = openmc.model.pack_spheres(radius=r_opyc, region=packing_region,
                                        pf=packing, seed=seed)
    trisos = [openmc.model.TRISO(r_opyc, triso_univ, c) for c in centers]
    n_particles = len(trisos)

    # background lattice for TRISO placement (speeds up tracking)
    compact_cell = openmc.Cell(region=compact_region)
    lb = np.array([-r_compact, -r_compact, 0.0])
    ub = np.array([ r_compact,  r_compact, H])
    shape = (6, 6, 4)
    pitch = (ub - lb) / shape
    bg = openmc.Material(name='compact matrix bg')
    bg.add_element('C', 1.0); bg.set_density('g/cm3', 1.70)
    bg.add_s_alpha_beta(sab); bg.temperature = temp
    lattice = openmc.model.create_triso_lattice(trisos, lb, pitch, shape, bg)
    compact_cell.fill = lattice

    c_hole  = openmc.Cell(fill=helium, region=-cyl_hole & zslab)
    c_slv   = openmc.Cell(fill=sleeve, region=+cyl_comp & -cyl_sleeve & zslab)
    c_chan  = openmc.Cell(fill=helium, region=+cyl_sleeve & -cyl_chan & zslab)
    c_blk   = openmc.Cell(fill=block,  region=+cyl_chan & -cyl_cell & zslab)

    root = openmc.Universe(cells=[c_hole, compact_cell, c_slv, c_chan, c_blk])
    geom = openmc.Geometry(root)

    mats = openmc.Materials([uo2, buff, ipyc, sic, opyc, matrix, sleeve, block,
                             helium, bg])
    return geom, mats, n_particles, r_cell

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--temp', type=float, default=294.0)
    ap.add_argument('--enrich', type=float, default=6.0)
    ap.add_argument('--packing', type=float, default=0.30)
    ap.add_argument('--sab', default='c_Graphite')
    ap.add_argument('--particles', type=int, default=20000)
    ap.add_argument('--batches', type=int, default=150)
    ap.add_argument('--inactive', type=int, default=40)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--nobp', action='store_true', help='disable smeared burnable poison')
    ap.add_argument('--prompt-only', dest='prompt_only', action='store_true',
                    help='disable delayed neutrons (k_prompt) for beta_eff by prompt method')
    args = ap.parse_args()

    geom, mats, npart, rcell = build(args.temp, args.enrich, args.packing,
                                     args.sab, args.seed, bp=not args.nobp)
    geom.export_to_xml()
    mats.export_to_xml()

    settings = openmc.Settings()
    settings.run_mode = 'eigenvalue'
    settings.particles = args.particles
    settings.batches = args.batches
    settings.inactive = args.inactive
    settings.temperature = {'method': 'interpolation', 'range': (250.0, 2500.0)}
    # source: uniform in the compact annulus
    lower = (-1.3, -1.3, 0.0); upper = (1.3, 1.3, 3.9)
    settings.source = openmc.IndependentSource(
        space=openmc.stats.Box(lower, upper, only_fissionable=True))
    settings.output = {'tallies': False}
    if args.prompt_only:
        settings.create_delayed_neutrons = False  # -> k_prompt; beta_eff = 1 - k_p/k
    settings.export_to_xml()
    print(f"# TRISO particles packed: {npart}, cell radius {rcell:.3f} cm, T={args.temp} K")

if __name__ == '__main__':
    main()

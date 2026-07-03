"""2-D Monte-Carlo view factors for the NSTF-style cavity cross-section.

The cavity is tall (6.7 m) compared with its horizontal dimensions
(1.32 m x ~1.0 m), so the radiation exchange is computed in the horizontal
cross-section (infinite-strip approximation) and applied per axial slice.

Geometry (x = distance from heated plate, y = across cavity width):
  - heated plate      : x = 0,        y in [0, W]
  - 12 riser ducts    : rectangles, front face at x = D_CAV, depth DUCT_D,
                        width DUCT_W, pitch PITCH, row centred in y
  - side walls        : y = 0 and y = W, x in [0, X_REAR]   (adiabatic)
  - rear wall         : x = X_REAR, y in [0, W]             (adiabatic)

Surface groups:
  0 plate | 1 riser fronts | 2 riser sides | 3 riser rears | 4 adiabatic walls
"""
import json
import os
import numpy as np

W = 1.3208          # cavity width, m (52 in)
D_CAV = 0.7066      # plate -> riser front face, m (baseline)
DUCT_W = 0.0508     # duct narrow (front/rear) face, m (2 in)
DUCT_D = 0.254      # duct wide (side) face depth, m (10 in)
PITCH = 0.10922     # duct centre-to-centre pitch, m (4.3 in nominal)
GAP_REAR = 0.05     # assumed clearance duct rear -> insulated rear wall, m
X_REAR = D_CAV + DUCT_D + GAP_REAR

N_DUCT = 12
ROW_SPAN = (N_DUCT - 1) * PITCH + DUCT_W
Y0 = (W - ROW_SPAN) / 2.0   # y of the first duct's lower edge

GROUPS = ["plate", "front", "side", "rear", "adiabatic"]

# per-unit-height areas (strip widths, m) of each group
AREAS = np.array([
    W,                      # plate
    N_DUCT * DUCT_W,        # fronts
    2 * N_DUCT * DUCT_D,    # sides
    N_DUCT * DUCT_W,        # rears
    2 * X_REAR + W,         # side walls + rear wall
])


def _segments():
    """list of (p0, p1, normal, group). Normals point into the cavity air."""
    segs = []
    segs.append(((0.0, 0.0), (0.0, W), (1.0, 0.0), 0))                 # plate
    for i in range(N_DUCT):
        ylo = Y0 + i * PITCH
        yhi = ylo + DUCT_W
        xf, xr = D_CAV, D_CAV + DUCT_D
        segs.append(((xf, ylo), (xf, yhi), (-1.0, 0.0), 1))            # front
        segs.append(((xr, ylo), (xr, yhi), (1.0, 0.0), 3))             # rear
        segs.append(((xf, ylo), (xr, ylo), (0.0, -1.0), 2))            # side lo
        segs.append(((xf, yhi), (xr, yhi), (0.0, 1.0), 2))             # side hi
    segs.append(((0.0, 0.0), (X_REAR, 0.0), (0.0, 1.0), 4))            # wall y=0
    segs.append(((0.0, W), (X_REAR, W), (0.0, -1.0), 4))               # wall y=W
    segs.append(((X_REAR, 0.0), (X_REAR, W), (-1.0, 0.0), 4))          # rear wall
    return segs


def compute_F(n_rays=400_000, seed=1):
    rng = np.random.default_rng(seed)
    segs = _segments()
    P0 = np.array([s[0] for s in segs])
    P1 = np.array([s[1] for s in segs])
    NRM = np.array([s[2] for s in segs])
    GRP = np.array([s[3] for s in segs])
    D = P1 - P0
    seg_len = np.linalg.norm(D, axis=1)

    F = np.zeros((5, 5))
    for g in range(5):
        idx = np.where(GRP == g)[0]
        w = seg_len[idx] / seg_len[idx].sum()
        # sample emitting segments in proportion to their length
        which = rng.choice(idx, size=n_rays, p=w)
        t = rng.random(n_rays)
        origin = P0[which] + t[:, None] * D[which]
        nrm = NRM[which]
        tang = np.stack([-nrm[:, 1], nrm[:, 0]], axis=1)
        # diffuse (Lambert) emission in 2-D: sin(theta) uniform in [-1,1]
        s = 2.0 * rng.random(n_rays) - 1.0
        c = np.sqrt(1.0 - s * s)
        dirs = c[:, None] * nrm + s[:, None] * tang
        origin = origin + 1e-9 * nrm

        hit_grp = _trace(origin, dirs, P0, P1, NRM, GRP, which)
        for gj in range(5):
            F[g, gj] = np.mean(hit_grp == gj)
    return F


def _trace(origin, dirs, P0, P1, NRM, GRP, which):
    n_rays = origin.shape[0]
    best_t = np.full(n_rays, np.inf)
    best_g = np.full(n_rays, -1, dtype=int)
    for j in range(len(P0)):
        p0, p1, nrm = P0[j], P1[j], NRM[j]
        e = p1 - p0
        # solve origin + t*dir = p0 + u*e
        denom = dirs[:, 0] * (-e[1]) - dirs[:, 1] * (-e[0])
        with np.errstate(divide="ignore", invalid="ignore"):
            dx = p0[0] - origin[:, 0]
            dy = p0[1] - origin[:, 1]
            t = (dx * (-e[1]) - dy * (-e[0])) / denom
            u = (dirs[:, 0] * dy - dirs[:, 1] * dx) / denom
        ok = (np.abs(denom) > 1e-14) & (t > 1e-9) & (u >= 0.0) & (u <= 1.0)
        # ray must approach the segment's front side
        ok &= (dirs @ nrm) < 0.0
        upd = ok & (t < best_t)
        best_t[upd] = t[upd]
        best_g[upd] = GRP[j]
    return best_g


def get_F(cache=None, n_rays=400_000):
    if cache is None:
        cache = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "viewfactors.json")
    if os.path.exists(cache):
        with open(cache) as f:
            d = json.load(f)
        return np.array(d["F"]), np.array(d["areas"])
    F = compute_F(n_rays)
    # enforce reciprocity + row-sum = 1 (symmetrise A_i F_ij)
    AF = (AREAS[:, None] * F + (AREAS[:, None] * F).T) / 2.0
    F = AF / AREAS[:, None]
    F = F / F.sum(axis=1, keepdims=True)
    with open(cache, "w") as f:
        json.dump({"F": F.tolist(), "areas": AREAS.tolist(),
                   "groups": GROUPS, "n_rays": n_rays}, f, indent=1)
    return F, AREAS


if __name__ == "__main__":
    F, A = get_F(cache="viewfactors.json")
    print("groups:", GROUPS)
    print("areas per unit height:", np.round(A, 4))
    print("F matrix:")
    for i, g in enumerate(GROUPS):
        print(f"{g:10s}", np.round(F[i], 4))

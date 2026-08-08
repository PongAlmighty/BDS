"""Turn the CAD hex nut into something a browser can drop 120 of.

The source is a dimensionally correct 1/4-20 nut whose internal thread is 95% of
its triangles and completely invisible at the size these things land on screen.
Drop that group, weld the duplicated vertices the exporter left behind, then
centre and normalise so the overlay can size it in world units instead of mm.
"""
import sys

SRC = '/Users/themightypong/Documents/3d model Folder/hex-nut-quarter-20.obj'
DST = '/Users/themightypong/Documents/PythonCode/BDS/nut.obj'
KEEP = {'hex_body', 'bearing_face_top', 'bearing_face_bottom'}

verts, norms, tris = [], [], []
cur = None
for line in open(SRC):
    if line.startswith('v '):
        verts.append(tuple(float(x) for x in line.split()[1:4]))
    elif line.startswith('vn '):
        norms.append(tuple(float(x) for x in line.split()[1:4]))
    elif line.startswith('o '):
        cur = line.split(None, 1)[1].strip()
    elif line.startswith('f ') and cur in KEEP:
        face = []
        for tok in line.split()[1:]:
            bits = tok.split('/')
            vi = int(bits[0]) - 1
            ni = int(bits[2]) - 1 if len(bits) > 2 and bits[2] else None
            face.append((vi, ni))
        for i in range(1, len(face) - 1):          # fan-triangulate, just in case
            tris.append((face[0], face[i], face[i + 1]))

print(f"kept {len(tris)} tris from {len(KEEP)} groups")

# Centre on the bounding box and scale so the largest dimension is 1.0, so the
# overlay picks a size in world units without knowing anything about millimetres.
xs = [verts[vi][0] for t in tris for vi, _ in t]
ys = [verts[vi][1] for t in tris for vi, _ in t]
zs = [verts[vi][2] for t in tris for vi, _ in t]
lo = (min(xs), min(ys), min(zs))
hi = (max(xs), max(ys), max(zs))
mid = tuple((lo[i] + hi[i]) / 2 for i in range(3))
scale = 1.0 / max(hi[i] - lo[i] for i in range(3))
print("source size mm:", ['%.2f' % ((hi[i] - lo[i]) * 1000) for i in range(3)])
print("normalised    :", ['%.3f' % ((hi[i] - lo[i]) * scale) for i in range(3)])

# Weld: the exporter emitted every triangle with its own copies of shared corners.
vmap, nmap, out_v, out_n, out_f = {}, {}, [], [], []


def key(vals):
    return tuple(round(c, 7) for c in vals)


for tri in tris:
    idx = []
    for vi, ni in tri:
        p = key(tuple((verts[vi][i] - mid[i]) * scale for i in range(3)))
        if p not in vmap:
            vmap[p] = len(out_v) + 1
            out_v.append(p)
        n = key(norms[ni]) if ni is not None else (0.0, 1.0, 0.0)
        if n not in nmap:
            nmap[n] = len(out_n) + 1
            out_n.append(n)
        idx.append((vmap[p], nmap[n]))
    out_f.append(idx)

with open(DST, 'w') as f:
    f.write("# 1/4-20 hex nut for the Bean Delivery System.\n")
    f.write("# Generated from hex-nut-quarter-20.obj: internal thread removed,\n")
    f.write("# vertices welded, centred, normalised to a 1.0 bounding box.\n")
    f.write("o nut\n")
    for v in out_v:
        f.write("v %.6f %.6f %.6f\n" % v)
    for n in out_n:
        f.write("vn %.4f %.4f %.4f\n" % n)
    for face in out_f:
        f.write("f " + " ".join("%d//%d" % (v, n) for v, n in face) + "\n")

print(f"verts {len(verts)} -> {len(out_v)}   normals {len(norms)} -> {len(out_n)}")
print("wrote", DST)

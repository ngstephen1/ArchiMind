"""Build an original ArchiMind designer piece in a fresh Blender scene.

Every piece is modelled from numeric profiles in metres (Blender X width, -Y
front, Z up) and dressed in physically based materials whose texture detail
comes from CC0 maps already released into the style-pack store
(``_viewer_assets/packs``): wood grain from the veneers, weave from the
fabrics. Fabrics are reduced to a neutral weave map so one CC0 scan can be
tinted to any upholstery colour through the glTF base-colour factor.

The Blender entry point is ``author_piece(output_directory, concept_id)``; the
CLI below accepts arguments after Blender's ``--`` separator. Each run writes
``piece.glb``, ``piece.blend``, ``front.png``, ``three-quarter.png`` and
``authoring.json`` (authoring schema 2) into a new directory.
"""

import argparse
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "src" / "archimind" / "_viewer_assets" / "packs"
ATTRIBUTION = (
    "Original ArchiMind geometry, proportions, finishes and studio lighting, "
    "modelled from numeric profiles in Blender. Texture detail is derived from "
    "CC0-1.0 Poly Haven maps released in the ArchiMind style-pack store; no "
    "external meshes."
)

# ---------------------------------------------------------------------------
# Finishes. kind: wood (veneer maps, multiplied by tint), fabric (neutral weave
# derived from a CC0 scan, tinted), plain (factors only).
# tile_m is the real-world size one texture repeat covers.
# ---------------------------------------------------------------------------
WEAVE_MEAN = 0.82  # sRGB mean of a derived weave map
FINISHES = {
    "Ash": dict(kind="wood", asset="polyhaven:ash_veneer", tint="FFFFFF", tile=0.9),
    "Pale oak": dict(
        kind="wood", asset="polyhaven:ash_veneer", tint="F2DCC0", tile=0.9
    ),
    "Smoked oak": dict(
        kind="wood", asset="polyhaven:ash_veneer", tint="A88A6C", tile=0.9
    ),
    "Walnut": dict(kind="wood", asset="polyhaven:dark_wood", tint="F4E4D8", tile=0.8),
    "Ebonised oak": dict(
        kind="wood", asset="polyhaven:dark_wood", tint="7A6A62", tile=0.8
    ),
    "Reclaimed oak": dict(
        kind="wood", asset="polyhaven:oak_wood_planks", tint="D8C8B4", tile=1.6
    ),
    "White lacquer": dict(kind="plain", color="EFECE6", roughness=0.32),
    "Black steel": dict(kind="plain", color="232323", roughness=0.42, metallic=1.0),
    "Brass": dict(kind="plain", color="C7A15A", roughness=0.28, metallic=1.0),
    "Opal glass": dict(kind="plain", color="F6F1E8", roughness=0.2, emission="8C7A62"),
    "Warm bulb": dict(kind="plain", color="FFF4E0", roughness=0.4, emission="FFE2B0"),
    "Oatmeal linen": dict(
        kind="fabric", asset="polyhaven:rough_linen", tint="CFC3AE", tile=0.28
    ),
    "White linen": dict(
        kind="fabric", asset="polyhaven:rough_linen", tint="ECE7DD", tile=0.28
    ),
    "Charcoal linen": dict(
        kind="fabric", asset="polyhaven:rough_linen", tint="56534F", tile=0.28
    ),
    "Clay linen": dict(
        kind="fabric", asset="polyhaven:rough_linen", tint="B9876A", tile=0.28
    ),
    "Sage linen": dict(
        kind="fabric", asset="polyhaven:rough_linen", tint="98A48C", tile=0.28
    ),
    "Mustard wool": dict(
        kind="fabric", asset="polyhaven:rough_linen", tint="C99A3A", tile=0.22
    ),
    "Teal wool": dict(
        kind="fabric", asset="polyhaven:rough_linen", tint="2F6A6A", tile=0.22
    ),
    "Stone linen": dict(
        kind="fabric", asset="polyhaven:rough_linen", tint="8E8A84", tile=0.28
    ),
    "Ivory weave": dict(
        kind="fabric", asset="polyhaven:rough_linen", tint="E4DED3", tile=0.2
    ),
    "Dove weave": dict(
        kind="fabric", asset="polyhaven:rough_linen", tint="B9B4AC", tile=0.2
    ),
    "Slate velvet": dict(
        kind="fabric", asset="polyhaven:velour_velvet", tint="5F6B78", tile=0.35
    ),
    "Moss velvet": dict(
        kind="fabric", asset="polyhaven:velour_velvet", tint="56684A", tile=0.35
    ),
    "Washi paper": dict(
        kind="fabric",
        asset="polyhaven:rough_linen",
        tint="F2ECDF",
        tile=0.18,
        emission="5E4E38",
    ),
}


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_linear(h):
    return tuple(srgb_to_linear(int(h[i : i + 2], 16) / 255) for i in (0, 2, 4))


# ---------------------------------------------------------------------------
# Pure geometry: profiles and revolve helpers (no bpy).
# ---------------------------------------------------------------------------
def revolve(profile, segments, closed=False):
    """Vertices/faces of a profile [(r, z)] revolved about Z.

    ``closed`` joins the last profile point back to the first (a shell with
    thickness); otherwise points with r == 0 become poles.
    """
    verts, rings = [], []
    for r, z in profile:
        if r < 1e-7 and not closed:
            rings.append([len(verts)])
            verts.append((0.0, 0.0, z))
            continue
        ring = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            ring.append(len(verts))
            verts.append((r * math.cos(a), r * math.sin(a), z))
        rings.append(ring)
    faces = []
    pairs = list(zip(rings, rings[1:]))
    if closed:
        pairs.append((rings[-1], rings[0]))
    for a, b in pairs:
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            faces += [(a[0], b[i], b[(i + 1) % segments]) for i in range(segments)]
        elif len(b) == 1:
            faces += [(a[i], b[0], a[(i + 1) % segments]) for i in range(segments)]
        else:
            faces += [
                (a[i], a[(i + 1) % segments], b[(i + 1) % segments], b[i])
                for i in range(segments)
            ]
    if not closed:
        if len(rings[0]) > 1:
            faces.append(tuple(reversed(rings[0])))
        if len(rings[-1]) > 1:
            faces.append(tuple(rings[-1]))
    return verts, faces


def shell(outer, thickness):
    """Closed (r, z) loop: the outer profile, then the same profile moved inward."""
    inner = [(max(r - thickness, 0.001), z) for r, z in reversed(outer)]
    return list(outer) + inner


# ---------------------------------------------------------------------------
# Blender kit
# ---------------------------------------------------------------------------
class Kit:
    def __init__(self, bpy, collection, materials):
        import bmesh

        self.bpy, self.bmesh, self.collection = bpy, bmesh, collection
        self.materials = materials
        self.parts = []

    # -- object plumbing --------------------------------------------------
    def _object(self, name, bm, finish, grain, smooth=True):
        mesh = self.bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        if smooth:
            mesh.shade_smooth()
        obj = self.bpy.data.objects.new(name, mesh)
        self.collection.objects.link(obj)
        mesh.materials.append(self.materials(finish))
        obj["grain"] = grain
        obj["finish"] = finish
        self.parts.append(obj)
        return obj

    def _bevel(self, obj, width, segments=3, harden=True):
        if width <= 0:
            return obj
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = width
        mod.segments = segments
        mod.limit_method = "ANGLE"
        mod.harden_normals = harden
        return obj

    def _subsurf(self, obj, levels):
        if levels:
            mod = obj.modifiers.new("Subdivision", "SUBSURF")
            mod.levels = mod.render_levels = levels
        return obj

    def _from_pydata(self, name, verts, faces, finish, grain, smooth=True):
        bm = self.bmesh.new()
        bverts = [bm.verts.new(v) for v in verts]
        for f in faces:
            bm.faces.new([bverts[i] for i in f])
        self.bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self._object(name, bm, finish, grain, smooth)

    # -- primitives -------------------------------------------------------
    def box(
        self, name, finish, x0, y0, z0, x1, y1, z1, bevel=0.004, segments=3, grain=None
    ):
        bm = self.bmesh.new()
        self.bmesh.ops.create_cube(bm, size=1.0)
        w, d, h = x1 - x0, y1 - y0, z1 - z0
        for v in bm.verts:
            v.co.x = (x0 + x1) / 2 + v.co.x * w
            v.co.y = (y0 + y1) / 2 + v.co.y * d
            v.co.z = (z0 + z1) / 2 + v.co.z * h
        grain = grain or "xyz"[max(range(3), key=lambda i: (w, d, h)[i])]
        obj = self._object(name, bm, finish, grain)
        return self._bevel(obj, min(bevel, 0.45 * min(w, d, h)), segments)

    def cushion(
        self, name, finish, x0, y0, z0, x1, y1, z1, puff=0.35, round_=0.03, tilt=0.0
    ):
        """A soft upholstered block: subdivided, crowned at the centre, rounded."""
        bm = self.bmesh.new()
        self.bmesh.ops.create_cube(bm, size=1.0)
        self.bmesh.ops.subdivide_edges(
            bm, edges=bm.edges[:], cuts=6, use_grid_fill=True
        )
        w, d, h = x1 - x0, y1 - y0, z1 - z0
        for v in bm.verts:
            u, s, t = v.co.x * 2, v.co.y * 2, v.co.z * 2  # -1..1
            # Crown: the faces bulge most at their centres; edges stay pinched.
            crown = (1 - u**4) * (1 - s**4)
            t *= 1 - puff * (1 - crown) * 0.5
            v.co.x = (x0 + x1) / 2 + u * w / 2
            v.co.y = (y0 + y1) / 2 + s * d / 2 + tilt * (t + 1) / 2
            v.co.z = (z0 + z1) / 2 + t * h / 2
        obj = self._object(name, bm, finish, "x")
        self._bevel(obj, min(round_, 0.3 * min(w, d, h)), 2, harden=False)
        return self._subsurf(obj, 1)

    def lathe(
        self,
        name,
        finish,
        profile,
        cx=0.0,
        cy=0.0,
        segments=40,
        closed=False,
        bevel=0.0,
        grain="z",
        subsurf=0,
    ):
        verts, faces = revolve(profile, segments, closed)
        verts = [(x + cx, y + cy, z) for x, y, z in verts]
        obj = self._from_pydata(name, verts, faces, finish, grain)
        self._bevel(obj, bevel, 2)
        return self._subsurf(obj, subsurf)

    def cylinder(
        self, name, finish, cx, cy, z0, z1, r0, r1=None, segments=32, bevel=0.002
    ):
        r1 = r0 if r1 is None else r1
        return self.lathe(
            name,
            finish,
            [(0, z0), (r0, z0), (r1, z1), (0, z1)],
            cx,
            cy,
            segments,
            bevel=bevel,
        )

    def rod(self, name, finish, p0, p1, r0, r1=None, segments=16):
        """A round member from p0 to p1 (radius r0 at p0, r1 at p1)."""
        from mathutils import Vector

        r1 = r0 if r1 is None else r1
        a, b = Vector(p0), Vector(p1)
        length = (b - a).length
        verts, faces = revolve([(0, 0), (r0, 0), (r1, length), (0, length)], segments)
        rot = Vector((0, 0, 1)).rotation_difference((b - a).normalized()).to_matrix()
        verts = [tuple(a + rot @ Vector(v)) for v in verts]
        return self._from_pydata(name, verts, faces, finish, "z")

    def sphere(self, name, finish, cx, cy, cz, r, segments=32, rings=16):
        bm = self.bmesh.new()
        self.bmesh.ops.create_uvsphere(
            bm, u_segments=segments, v_segments=rings, radius=r
        )
        for v in bm.verts:
            v.co.x += cx
            v.co.y += cy
            v.co.z += cz
        return self._object(name, bm, finish, "z")


# ---------------------------------------------------------------------------
# Piece builders. Each draws inside its declared W x D x H, floor-centred.
# ---------------------------------------------------------------------------
def _bedding(k, w, d, mattress_z, head_y, linen, duvet, throw, pillows=2):
    """Mattress, duvet, pillows and a folded throw for a bed of width w."""
    mw, md = w - 0.10, d - 0.14
    y0 = -d / 2 + 0.05
    y1 = y0 + md
    k.cushion(
        "Mattress",
        linen,
        -mw / 2,
        y0,
        mattress_z,
        mw / 2,
        y1,
        mattress_z + 0.17,
        puff=0.12,
        round_=0.035,
    )
    # The duvet drapes over the foot and the sides and is turned back at the head.
    k.cushion(
        "Duvet",
        duvet,
        -mw / 2 - 0.02,
        y0 - 0.02,
        mattress_z + 0.09,
        mw / 2 + 0.02,
        y1 - 0.42,
        mattress_z + 0.215,
        puff=0.25,
        round_=0.045,
    )
    k.cushion(
        "Turned-down sheet",
        linen,
        -mw / 2 - 0.015,
        y1 - 0.47,
        mattress_z + 0.13,
        mw / 2 + 0.015,
        y1 - 0.36,
        mattress_z + 0.225,
        puff=0.3,
        round_=0.04,
    )
    k.cushion(
        "Folded throw",
        throw,
        -mw / 2 - 0.025,
        y0 + 0.18,
        mattress_z + 0.20,
        mw / 2 + 0.025,
        y0 + 0.52,
        mattress_z + 0.245,
        puff=0.2,
        round_=0.018,
    )
    pw = (mw - 0.12) / pillows
    for i in range(pillows):
        x0 = -mw / 2 + 0.04 + i * (pw + 0.04)
        k.cushion(
            f"Pillow {i + 1}",
            linen,
            x0,
            head_y - 0.42,
            mattress_z + 0.16,
            x0 + pw,
            head_y - 0.06,
            mattress_z + 0.33,
            puff=0.75,
            round_=0.05,
            tilt=0.04,
        )


def bed_japandi(k, w, d, h):
    # A recessed plinth lifts a solid ash deck; slatted low headboard.
    k.box(
        "Recessed plinth",
        "Smoked oak",
        -w / 2 + 0.16,
        -d / 2 + 0.18,
        0,
        w / 2 - 0.16,
        d / 2 - 0.20,
        0.10,
        bevel=0.003,
    )
    k.box(
        "Ash platform deck",
        "Ash",
        -w / 2,
        -d / 2,
        0.10,
        w / 2,
        d / 2 - 0.05,
        0.165,
        bevel=0.008,
        grain="y",
    )
    k.box(
        "Headboard rail",
        "Ash",
        -w / 2,
        d / 2 - 0.05,
        0.10,
        w / 2,
        d / 2,
        0.16,
        bevel=0.006,
        grain="x",
    )
    k.box(
        "Headboard cap",
        "Ash",
        -w / 2,
        d / 2 - 0.055,
        h - 0.035,
        w / 2,
        d / 2,
        h,
        bevel=0.008,
        grain="x",
    )
    n = 13
    pitch = (w - 0.06) / n
    for i in range(n):
        x = -w / 2 + 0.03 + (i + 0.5) * pitch
        k.box(
            f"Slat {i + 1}",
            "Ash",
            x - 0.026,
            d / 2 - 0.045,
            0.16,
            x + 0.026,
            d / 2 - 0.01,
            h - 0.035,
            bevel=0.004,
            grain="z",
        )
    _bedding(
        k, w, d, 0.165, d / 2 - 0.05, "White linen", "Oatmeal linen", "Charcoal linen"
    )


def bed_scandinavian(k, w, d, h):
    leg = 0.055
    for sx in (-1, 1):
        for sy in (-1, 1):
            x = sx * (w / 2 - leg / 2 - 0.01)
            y = sy * (d / 2 - leg / 2 - 0.01)
            k.cylinder(
                f"Leg {'LR'[sx > 0]}{'FB'[sy > 0]}",
                "Pale oak",
                x,
                y,
                0,
                0.30,
                0.022,
                0.028,
            )
    k.box(
        "Left rail",
        "Pale oak",
        -w / 2,
        -d / 2 + 0.03,
        0.15,
        -w / 2 + 0.045,
        d / 2 - 0.06,
        0.32,
        bevel=0.008,
        grain="y",
    )
    k.box(
        "Right rail",
        "Pale oak",
        w / 2 - 0.045,
        -d / 2 + 0.03,
        0.15,
        w / 2,
        d / 2 - 0.06,
        0.32,
        bevel=0.008,
        grain="y",
    )
    k.box(
        "Foot rail",
        "Pale oak",
        -w / 2,
        -d / 2,
        0.15,
        w / 2,
        -d / 2 + 0.045,
        0.32,
        bevel=0.008,
        grain="x",
    )
    k.box(
        "Slatted base",
        "Pale oak",
        -w / 2 + 0.045,
        -d / 2 + 0.045,
        0.22,
        w / 2 - 0.045,
        d / 2 - 0.1,
        0.24,
        bevel=0.002,
        grain="y",
    )
    k.box(
        "Headboard frame",
        "Pale oak",
        -w / 2,
        d / 2 - 0.06,
        0.15,
        w / 2,
        d / 2,
        h,
        bevel=0.012,
        grain="x",
    )
    k.cushion(
        "Upholstered headboard",
        "Ivory weave",
        -w / 2 + 0.05,
        d / 2 - 0.12,
        0.34,
        w / 2 - 0.05,
        d / 2 - 0.05,
        h - 0.03,
        puff=0.5,
        round_=0.03,
    )
    _bedding(k, w, d, 0.24, d / 2 - 0.12, "White linen", "Ivory weave", "Sage linen")


def bed_mid_century(k, w, d, h):
    for sx in (-1, 1):
        for sy in (-1, 1):
            foot = (sx * (w / 2 - 0.05), sy * (d / 2 - 0.06), 0)
            top = (sx * (w / 2 - 0.09), sy * (d / 2 - 0.11), 0.19)
            k.rod(
                f"Tapered leg {'LR'[sx > 0]}{'FB'[sy > 0]}",
                "Walnut",
                foot,
                top,
                0.014,
                0.024,
            )
            k.cylinder(
                f"Brass sabot {'LR'[sx > 0]}{'FB'[sy > 0]}",
                "Brass",
                foot[0],
                foot[1],
                0,
                0.025,
                0.0155,
                0.016,
                segments=20,
                bevel=0.001,
            )
    k.box(
        "Walnut frame",
        "Walnut",
        -w / 2 + 0.02,
        -d / 2 + 0.02,
        0.18,
        w / 2 - 0.02,
        d / 2 - 0.07,
        0.265,
        bevel=0.012,
        grain="y",
    )
    k.box(
        "Headboard",
        "Walnut",
        -w / 2,
        d / 2 - 0.07,
        0.18,
        w / 2,
        d / 2,
        h,
        bevel=0.014,
        grain="x",
    )
    for i, z in enumerate((0.33, 0.42, 0.51)):
        k.box(
            f"Headboard reveal {i + 1}",
            "Ebonised oak",
            -w / 2 + 0.03,
            d / 2 - 0.076,
            z,
            w / 2 - 0.03,
            d / 2 - 0.06,
            z + 0.008,
            bevel=0.0,
            grain="x",
        )
    _bedding(k, w, d, 0.265, d / 2 - 0.07, "White linen", "Stone linen", "Mustard wool")


def bed_modern_classic(k, w, d, h):
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - 0.09), sy * (d / 2 - 0.12)
            k.lathe(
                f"Brass bun foot {'LR'[sx > 0]}{'FB'[sy > 0]}",
                "Brass",
                [
                    (0, 0),
                    (0.026, 0),
                    (0.034, 0.02),
                    (0.036, 0.045),
                    (0.028, 0.07),
                    (0.03, 0.08),
                    (0, 0.08),
                ],
                x,
                y,
                segments=28,
            )
    k.cushion(
        "Upholstered base",
        "Slate velvet",
        -w / 2 + 0.01,
        -d / 2,
        0.08,
        w / 2 - 0.01,
        d / 2 - 0.1,
        0.265,
        puff=0.15,
        round_=0.04,
    )
    k.box(
        "Headboard back",
        "Slate velvet",
        -w / 2,
        d / 2 - 0.05,
        0.08,
        w / 2,
        d / 2,
        h,
        bevel=0.02,
        segments=4,
    )
    n = 8
    pitch = (w - 0.04) / n
    for i in range(n):
        x0 = -w / 2 + 0.02 + i * pitch
        k.cushion(
            f"Channel {i + 1}",
            "Slate velvet",
            x0 + 0.003,
            d / 2 - 0.11,
            0.265,
            x0 + pitch - 0.003,
            d / 2 - 0.045,
            h - 0.015,
            puff=0.7,
            round_=0.03,
        )
    _bedding(k, w, d, 0.265, d / 2 - 0.11, "White linen", "White linen", "Moss velvet")


def bed_industrial(k, w, d, h):
    t = 0.04
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - t / 2), sy * (d / 2 - t / 2)
            k.box(
                f"Steel post {'LR'[sx > 0]}{'FB'[sy > 0]}",
                "Black steel",
                x - t / 2,
                y - t / 2,
                0,
                x + t / 2,
                y + t / 2,
                h if sy > 0 else 0.34,
                bevel=0.003,
            )
    for name, (x0, y0, x1, y1) in {
        "Left rail": (-w / 2, -d / 2 + t, -w / 2 + t, d / 2 - t),
        "Right rail": (w / 2 - t, -d / 2 + t, w / 2, d / 2 - t),
        "Foot rail": (-w / 2 + t, -d / 2, w / 2 - t, -d / 2 + t),
    }.items():
        k.box(name, "Black steel", x0, y0, 0.24, x1, y1, 0.30, bevel=0.003)
    for i, z in enumerate((0.30, h - 0.03)):
        k.box(
            f"Head rail {i + 1}",
            "Black steel",
            -w / 2 + t,
            d / 2 - t,
            z - 0.015,
            w / 2 - t,
            d / 2,
            z + 0.015,
            bevel=0.003,
        )
    k.box(
        "Reclaimed oak headboard",
        "Reclaimed oak",
        -w / 2 + t,
        d / 2 - 0.032,
        0.315,
        w / 2 - t,
        d / 2 - 0.008,
        h - 0.045,
        bevel=0.004,
        grain="x",
    )
    k.box(
        "Base deck",
        "Reclaimed oak",
        -w / 2 + t,
        -d / 2 + t,
        0.26,
        w / 2 - t,
        d / 2 - t,
        0.29,
        bevel=0.003,
        grain="y",
    )
    _bedding(k, w, d, 0.29, d / 2 - t, "Stone linen", "Charcoal linen", "Clay linen")


def _sofa_cushions(
    k, x0, x1, seat_z, front_y, back_y, top_z, fabric, count, back_tilt=0.06
):
    pitch = (x1 - x0) / count
    for i in range(count):
        a, b = x0 + i * pitch + 0.004, x0 + (i + 1) * pitch - 0.004
        k.cushion(
            f"Seat cushion {i + 1}",
            fabric,
            a,
            front_y,
            seat_z,
            b,
            back_y - 0.12,
            seat_z + 0.13,
            puff=0.35,
            round_=0.035,
        )
        k.cushion(
            f"Back cushion {i + 1}",
            fabric,
            a,
            back_y - 0.2,
            seat_z + 0.11,
            b,
            back_y,
            top_z,
            puff=0.55,
            round_=0.045,
            tilt=back_tilt,
        )


def sofa_japandi(k, w, d, h):
    # Exposed ash frame with low linen cushions.
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - 0.05), sy * (d / 2 - 0.05)
            k.box(
                f"Ash leg {'LR'[sx > 0]}{'FB'[sy > 0]}",
                "Ash",
                x - 0.025,
                y - 0.025,
                0,
                x + 0.025,
                y + 0.025,
                0.14,
                bevel=0.005,
                grain="z",
            )
    k.box(
        "Ash seat frame",
        "Ash",
        -w / 2 + 0.01,
        -d / 2 + 0.01,
        0.14,
        w / 2 - 0.01,
        d / 2 - 0.01,
        0.20,
        bevel=0.008,
        grain="x",
    )
    k.box(
        "Back panel",
        "Oatmeal linen",
        -w / 2 + 0.07,
        d / 2 - 0.06,
        0.20,
        w / 2 - 0.07,
        d / 2 - 0.01,
        h - 0.08,
        bevel=0.02,
    )
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.035)
        k.box(
            f"Ash arm {'LR'[sx > 0]}",
            "Ash",
            x - 0.035,
            -d / 2,
            0.20,
            x + 0.035,
            d / 2,
            0.50,
            bevel=0.01,
            grain="y",
        )
    _sofa_cushions(
        k,
        -w / 2 + 0.075,
        w / 2 - 0.075,
        0.20,
        -d / 2 + 0.03,
        d / 2 - 0.05,
        h,
        "Oatmeal linen",
        3,
    )


def sofa_scandinavian(k, w, d, h):
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - 0.12), sy * (d / 2 - 0.1)
            k.cylinder(
                f"Oak leg {'LR'[sx > 0]}{'FB'[sy > 0]}",
                "Pale oak",
                x,
                y,
                0,
                0.16,
                0.016,
                0.022,
            )
    k.cushion(
        "Upholstered base",
        "Dove weave",
        -w / 2,
        -d / 2,
        0.15,
        w / 2,
        d / 2,
        0.36,
        puff=0.1,
        round_=0.04,
    )
    k.cushion(
        "Upholstered back",
        "Dove weave",
        -w / 2,
        d / 2 - 0.17,
        0.34,
        w / 2,
        d / 2,
        h - 0.06,
        puff=0.15,
        round_=0.05,
    )
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.08)
        k.cushion(
            f"Rounded arm {'LR'[sx > 0]}",
            "Dove weave",
            x - 0.08,
            -d / 2,
            0.34,
            x + 0.08,
            d / 2 - 0.1,
            0.60,
            puff=0.3,
            round_=0.06,
        )
    _sofa_cushions(
        k,
        -w / 2 + 0.16,
        w / 2 - 0.16,
        0.36,
        -d / 2 + 0.02,
        d / 2 - 0.12,
        h,
        "Ivory weave",
        2,
        back_tilt=0.05,
    )


def sofa_mid_century(k, w, d, h):
    for sx in (-1, 1):
        for sy in (-1, 1):
            foot = (sx * (w / 2 - 0.06), sy * (d / 2 - 0.06), 0)
            top = (sx * (w / 2 - 0.1), sy * (d / 2 - 0.1), 0.17)
            k.rod(
                f"Walnut leg {'LR'[sx > 0]}{'FB'[sy > 0]}",
                "Walnut",
                foot,
                top,
                0.013,
                0.022,
            )
    k.box(
        "Walnut plinth",
        "Walnut",
        -w / 2 + 0.04,
        -d / 2 + 0.04,
        0.16,
        w / 2 - 0.04,
        d / 2 - 0.04,
        0.19,
        bevel=0.008,
        grain="x",
    )
    k.box(
        "Upholstered body",
        "Teal wool",
        -w / 2,
        -d / 2 + 0.02,
        0.19,
        w / 2,
        d / 2,
        0.40,
        bevel=0.025,
        segments=4,
    )
    k.box(
        "Back frame",
        "Teal wool",
        -w / 2,
        d / 2 - 0.12,
        0.40,
        w / 2,
        d / 2,
        h - 0.12,
        bevel=0.03,
        segments=4,
    )
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.05)
        k.box(
            f"Track arm {'LR'[sx > 0]}",
            "Teal wool",
            x - 0.05,
            -d / 2 + 0.02,
            0.40,
            x + 0.05,
            d / 2,
            0.60,
            bevel=0.03,
            segments=4,
        )
    _sofa_cushions(
        k,
        -w / 2 + 0.1,
        w / 2 - 0.1,
        0.40,
        -d / 2 + 0.03,
        d / 2 - 0.1,
        h,
        "Teal wool",
        2,
        back_tilt=0.03,
    )
    for sx in (-1, 1):
        k.cushion(
            f"Bolster cushion {'LR'[sx > 0]}",
            "Mustard wool",
            sx * (w / 2 - 0.38) - 0.2,
            d / 2 - 0.38,
            0.52,
            sx * (w / 2 - 0.38) + 0.2,
            d / 2 - 0.24,
            0.80 * h,
            puff=0.8,
            round_=0.05,
            tilt=0.03,
        )


def desk_japandi(k, w, d, h):
    # A floating ash top over a recessed smoked-oak apron (10 mm shadow gap),
    # carried by two trestle end frames joined by a slatted low shelf.
    top_z = h - 0.032
    k.box(
        "Ash top", "Ash", -w / 2, -d / 2, top_z, w / 2, d / 2, h, bevel=0.008, grain="x"
    )
    apron_top = top_z - 0.01
    k.box(
        "Shadow-gap apron",
        "Smoked oak",
        -w / 2 + 0.11,
        -d / 2 + 0.07,
        apron_top - 0.07,
        w / 2 - 0.11,
        d / 2 - 0.05,
        apron_top,
        bevel=0.003,
        grain="x",
    )
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.13)
        side = "LR"[sx > 0]
        for sy in (-1, 1):
            y = sy * (d / 2 - 0.09)
            k.box(
                f"Post {side}{'FB'[sy > 0]}",
                "Ash",
                x - 0.019,
                y - 0.019,
                0.03,
                x + 0.019,
                y + 0.019,
                apron_top,
                bevel=0.004,
                grain="z",
            )
        k.box(
            f"Foot runner {side}",
            "Ash",
            x - 0.024,
            -d / 2 + 0.04,
            0,
            x + 0.024,
            d / 2 - 0.04,
            0.03,
            bevel=0.005,
            grain="y",
        )
        k.box(
            f"Upper rail {side}",
            "Ash",
            x - 0.016,
            -d / 2 + 0.07,
            apron_top - 0.06,
            x + 0.016,
            d / 2 - 0.07,
            apron_top - 0.012,
            bevel=0.003,
            grain="y",
        )
        k.box(
            f"Shelf bearer {side}",
            "Ash",
            x - 0.016,
            -d / 2 + 0.07,
            0.15,
            x + 0.016,
            d / 2 - 0.07,
            0.18,
            bevel=0.003,
            grain="y",
        )
    n, x0, x1 = 9, -w / 2 + 0.115, w / 2 - 0.115
    depth = d - 0.2
    pitch = depth / n
    for i in range(n):
        y = -d / 2 + 0.1 + i * pitch
        k.box(
            f"Shelf slat {i + 1}",
            "Ash",
            x0,
            y + 0.006,
            0.18,
            x1,
            y + pitch - 0.006,
            0.198,
            bevel=0.003,
            grain="x",
        )
    dx0, dx1 = w / 2 - 0.56, w / 2 - 0.15
    k.box(
        "Drawer front",
        "Ash",
        dx0,
        -d / 2 + 0.065,
        apron_top - 0.068,
        dx1,
        -d / 2 + 0.085,
        apron_top - 0.004,
        bevel=0.003,
        grain="x",
    )
    k.box(
        "Finger pull",
        "Ebonised oak",
        (dx0 + dx1) / 2 - 0.07,
        -d / 2 + 0.06,
        apron_top - 0.016,
        (dx0 + dx1) / 2 + 0.07,
        -d / 2 + 0.07,
        apron_top - 0.008,
        bevel=0.0,
        grain="x",
    )


def desk_mid_century(k, w, d, h):
    k.box(
        "Walnut top",
        "Walnut",
        -w / 2,
        -d / 2,
        h - 0.03,
        w / 2,
        d / 2,
        h,
        bevel=0.009,
        grain="x",
    )
    k.box(
        "Drawer case",
        "Walnut",
        -w / 2 + 0.06,
        -d / 2 + 0.04,
        h - 0.17,
        -w / 2 + 0.58,
        d / 2 - 0.06,
        h - 0.03,
        bevel=0.006,
        grain="x",
    )
    for i, z in enumerate((h - 0.165, h - 0.1)):
        k.box(
            f"Drawer front {i + 1}",
            "Walnut",
            -w / 2 + 0.07,
            -d / 2 + 0.035,
            z,
            -w / 2 + 0.57,
            -d / 2 + 0.042,
            z + 0.06,
            bevel=0.003,
            grain="x",
        )
        k.box(
            f"Brass pull {i + 1}",
            "Brass",
            -w / 2 + 0.27,
            -d / 2 + 0.02,
            z + 0.026,
            -w / 2 + 0.37,
            -d / 2 + 0.035,
            z + 0.036,
            bevel=0.003,
        )
    for sx in (-1, 1):
        for sy in (-1, 1):
            foot = (sx * (w / 2 - 0.05), sy * (d / 2 - 0.05), 0)
            top = (sx * (w / 2 - 0.1), sy * (d / 2 - 0.09), h - 0.03)
            k.rod(
                f"Tapered leg {'LR'[sx > 0]}{'FB'[sy > 0]}",
                "Walnut",
                foot,
                top,
                0.012,
                0.021,
            )
            k.cylinder(
                f"Brass ferrule {'LR'[sx > 0]}{'FB'[sy > 0]}",
                "Brass",
                foot[0],
                foot[1],
                0,
                0.035,
                0.0135,
                0.0145,
                segments=20,
                bevel=0.0,
            )


def desk_modern_classic(k, w, d, h):
    k.box(
        "Ebonised top",
        "Ebonised oak",
        -w / 2,
        -d / 2,
        h - 0.032,
        w / 2,
        d / 2,
        h,
        bevel=0.01,
        grain="x",
    )
    k.box(
        "Brass edge band",
        "Brass",
        -w / 2 + 0.004,
        -d / 2 + 0.004,
        h - 0.036,
        w / 2 - 0.004,
        d / 2 - 0.004,
        h - 0.031,
        bevel=0.0,
    )
    k.box(
        "Apron",
        "Ebonised oak",
        -w / 2 + 0.05,
        -d / 2 + 0.05,
        h - 0.15,
        w / 2 - 0.05,
        d / 2 - 0.05,
        h - 0.036,
        bevel=0.004,
        grain="x",
    )
    for i, x in enumerate((-w / 4, w / 4)):
        k.box(
            f"Drawer panel {i + 1}",
            "Ebonised oak",
            x - 0.26,
            -d / 2 + 0.042,
            h - 0.14,
            x + 0.26,
            -d / 2 + 0.05,
            h - 0.046,
            bevel=0.003,
            grain="x",
        )
        knob = k.lathe(
            f"Brass knob {i + 1}",
            "Brass",
            [
                (0, 0),
                (0.006, 0),
                (0.005, 0.012),
                (0.012, 0.018),
                (0.01, 0.026),
                (0, 0.028),
            ],
            0,
            0,
            segments=20,
        )
        knob.rotation_euler = (math.pi / 2, 0, 0)
        knob.location = (x, -d / 2 + 0.043, h - 0.093)
    profile = [
        (0, 0),
        (0.016, 0),
        (0.018, 0.04),
        (0.013, 0.08),
        (0.016, 0.35),
        (0.022, 0.5),
        (0.02, 0.56),
        (0.026, 0.58),
        (0.026, h - 0.15),
        (0, h - 0.15),
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - 0.075), sy * (d / 2 - 0.075)
            k.lathe(
                f"Turned leg {'LR'[sx > 0]}{'FB'[sy > 0]}",
                "Ebonised oak",
                profile,
                x,
                y,
                segments=24,
            )
            k.cylinder(
                f"Brass cup {'LR'[sx > 0]}{'FB'[sy > 0]}",
                "Brass",
                x,
                y,
                0,
                0.03,
                0.019,
                0.02,
                segments=20,
                bevel=0.0,
            )


def _shelves(k, w, d, h, carcass, shelf, base_h, top_t, shelves_z, back):
    t = 0.022
    k.box(
        "Left side",
        carcass,
        -w / 2,
        -d / 2,
        0,
        -w / 2 + t,
        d / 2,
        h - top_t,
        bevel=0.003,
        grain="z",
    )
    k.box(
        "Right side",
        carcass,
        w / 2 - t,
        -d / 2,
        0,
        w / 2,
        d / 2,
        h - top_t,
        bevel=0.003,
        grain="z",
    )
    k.box(
        "Back panel",
        back,
        -w / 2 + t,
        d / 2 - 0.012,
        base_h,
        w / 2 - t,
        d / 2,
        h - top_t,
        bevel=0.0,
        grain="z",
    )
    k.box(
        "Plinth",
        carcass,
        -w / 2 + t,
        -d / 2 + 0.03,
        0,
        w / 2 - t,
        d / 2 - 0.012,
        base_h,
        bevel=0.002,
        grain="x",
    )
    for i, z in enumerate(shelves_z):
        k.box(
            f"Shelf {i + 1}",
            shelf,
            -w / 2 + t,
            -d / 2 + 0.012,
            z,
            w / 2 - t,
            d / 2 - 0.012,
            z + 0.022,
            bevel=0.003,
            grain="x",
        )


def storage_japandi(k, w, d, h):
    _shelves(
        k, w, d, h, "Ash", "Ash", 0.06, 0.03, (0.06, 0.62, 0.98, 1.34), "Smoked oak"
    )
    k.box(
        "Top",
        "Ash",
        -w / 2 - 0.0,
        -d / 2,
        h - 0.03,
        w / 2,
        d / 2,
        h,
        bevel=0.006,
        grain="x",
    )
    # Two shoji-style sliding doors: washi panels behind a fine ash grid.
    for i, (x0, x1, y) in enumerate(
        (
            (-w / 2 + 0.022, 0.005, -d / 2 + 0.03),
            (-0.005, w / 2 - 0.022, -d / 2 + 0.012),
        )
    ):
        k.box(
            f"Washi panel {i + 1}",
            "Washi paper",
            x0 + 0.02,
            y + 0.006,
            0.1,
            x1 - 0.02,
            y + 0.01,
            0.6,
            bevel=0.0,
        )
        k.box(
            f"Door frame top {i + 1}",
            "Ash",
            x0,
            y,
            0.58,
            x1,
            y + 0.018,
            0.6,
            bevel=0.002,
        )
        k.box(
            f"Door frame bottom {i + 1}",
            "Ash",
            x0,
            y,
            0.08,
            x1,
            y + 0.018,
            0.1,
            bevel=0.002,
        )
        for j, x in enumerate((x0, x1 - 0.02)):
            k.box(
                f"Door stile {i + 1}.{j + 1}",
                "Ash",
                x,
                y,
                0.08,
                x + 0.02,
                y + 0.018,
                0.6,
                bevel=0.002,
                grain="z",
            )
        for j in range(1, 4):
            z = 0.1 + j * 0.125
            k.box(
                f"Kumiko bar {i + 1}.{j}",
                "Ash",
                x0 + 0.02,
                y + 0.002,
                z - 0.004,
                x1 - 0.02,
                y + 0.008,
                z + 0.004,
                bevel=0.0,
            )
        xm = (x0 + x1) / 2
        k.box(
            f"Kumiko upright {i + 1}",
            "Ash",
            xm - 0.004,
            y + 0.002,
            0.1,
            xm + 0.004,
            y + 0.008,
            0.58,
            bevel=0.0,
            grain="z",
        )


def storage_scandinavian(k, w, d, h):
    _shelves(
        k,
        w,
        d,
        h,
        "White lacquer",
        "Pale oak",
        0.08,
        0.025,
        (0.08, 0.66, 1.04, 1.42),
        "White lacquer",
    )
    k.box(
        "Top",
        "Pale oak",
        -w / 2,
        -d / 2,
        h - 0.025,
        w / 2,
        d / 2,
        h,
        bevel=0.006,
        grain="x",
    )
    for i, (x0, x1) in enumerate(((-w / 2 + 0.024, -0.002), (0.002, w / 2 - 0.024))):
        k.box(
            f"Door {i + 1}",
            "White lacquer",
            x0,
            -d / 2 + 0.02,
            0.1,
            x1,
            -d / 2 + 0.038,
            0.64,
            bevel=0.003,
            grain="z",
        )
        x = x1 - 0.05 if i == 0 else x0 + 0.05
        knob = k.cylinder(
            f"Oak knob {i + 1}",
            "Pale oak",
            0,
            0,
            0,
            0.02,
            0.014,
            0.012,
            segments=20,
            bevel=0.002,
        )
        knob.rotation_euler = (math.pi / 2, 0, 0)
        knob.location = (x, -d / 2 + 0.02, 0.37)


def storage_modern_classic(k, w, d, h):
    inset = 0.02
    k.box(
        "Cornice",
        "Ebonised oak",
        -w / 2,
        -d / 2,
        h - 0.05,
        w / 2,
        d / 2,
        h,
        bevel=0.012,
        segments=4,
        grain="x",
    )
    k.box(
        "Base moulding",
        "Ebonised oak",
        -w / 2,
        -d / 2,
        0,
        w / 2,
        d / 2,
        0.09,
        bevel=0.01,
        segments=4,
        grain="x",
    )
    sub_w, sub_d = w - 2 * inset, d - 2 * inset
    k.box(
        "Left side",
        "Ebonised oak",
        -sub_w / 2,
        -sub_d / 2,
        0.09,
        -sub_w / 2 + 0.025,
        sub_d / 2,
        h - 0.05,
        bevel=0.003,
        grain="z",
    )
    k.box(
        "Right side",
        "Ebonised oak",
        sub_w / 2 - 0.025,
        -sub_d / 2,
        0.09,
        sub_w / 2,
        sub_d / 2,
        h - 0.05,
        bevel=0.003,
        grain="z",
    )
    k.box(
        "Back panel",
        "Slate velvet",
        -sub_w / 2 + 0.025,
        sub_d / 2 - 0.012,
        0.09,
        sub_w / 2 - 0.025,
        sub_d / 2,
        h - 0.05,
        bevel=0.0,
    )
    for i, z in enumerate((0.09, 0.72, 1.06, 1.40)):
        k.box(
            f"Shelf {i + 1}",
            "Ebonised oak",
            -sub_w / 2 + 0.025,
            -sub_d / 2,
            z,
            sub_w / 2 - 0.025,
            sub_d / 2 - 0.012,
            z + 0.025,
            bevel=0.003,
            grain="x",
        )
        k.box(
            f"Brass shelf lip {i + 1}",
            "Brass",
            -sub_w / 2 + 0.025,
            -sub_d / 2 - 0.003,
            z + 0.02,
            sub_w / 2 - 0.025,
            -sub_d / 2 + 0.002,
            z + 0.025,
            bevel=0.0,
        )
    for i, (x0, x1) in enumerate(
        ((-sub_w / 2 + 0.027, -0.002), (0.002, sub_w / 2 - 0.027))
    ):
        y = -sub_d / 2 - 0.004
        k.box(
            f"Door {i + 1}",
            "Ebonised oak",
            x0,
            y,
            0.115,
            x1,
            y + 0.02,
            0.70,
            bevel=0.004,
            grain="z",
        )
        k.box(
            f"Raised panel {i + 1}",
            "Ebonised oak",
            x0 + 0.05,
            y - 0.006,
            0.17,
            x1 - 0.05,
            y + 0.004,
            0.65,
            bevel=0.01,
            segments=4,
            grain="z",
        )
        x = x1 - 0.035 if i == 0 else x0 + 0.035
        k.sphere(f"Brass knob {i + 1}", "Brass", x, y - 0.004, 0.42, 0.011, 16, 10)


def sideboard_mid_century(k, w, d, h):
    for sx in (-1, 1):
        for sy in (-1, 1):
            foot = (sx * (w / 2 - 0.08), sy * (d / 2 - 0.06), 0)
            top = (sx * (w / 2 - 0.12), sy * (d / 2 - 0.09), 0.2)
            k.rod(
                f"Tapered leg {'LR'[sx > 0]}{'FB'[sy > 0]}",
                "Walnut",
                foot,
                top,
                0.012,
                0.02,
            )
    front = -d / 2 + 0.014
    k.box(
        "Carcass",
        "Walnut",
        -w / 2,
        front + 0.012,
        0.19,
        w / 2,
        d / 2,
        h,
        bevel=0.01,
        grain="x",
    )
    pitch = (w - 0.04) / 4
    for i in range(4):
        x0 = -w / 2 + 0.02 + i * pitch
        k.box(
            f"Door {i + 1}",
            "Walnut",
            x0 + 0.003,
            front,
            0.21,
            x0 + pitch - 0.003,
            front + 0.012,
            h - 0.025,
            bevel=0.003,
            grain="z",
        )
        for j in range(1, 7):
            x = x0 + j * pitch / 7
            k.box(
                f"Door groove {i + 1}.{j}",
                "Ebonised oak",
                x - 0.002,
                front - 0.0005,
                0.24,
                x + 0.002,
                front + 0.001,
                h - 0.055,
                bevel=0.0,
                grain="z",
            )
        px = x0 + (pitch - 0.012 if i % 2 == 0 else 0.012)
        k.box(
            f"Brass pull {i + 1}",
            "Brass",
            px - 0.004,
            -d / 2,
            0.42,
            px + 0.004,
            front,
            0.56,
            bevel=0.002,
        )


def floor_lamp_mid_century(k, w, d, h):
    r = w / 2
    hub = (0, 0, 1.12)
    for i in range(3):
        a = math.radians(90 + 120 * i)
        foot = (0.165 * math.cos(a), 0.165 * math.sin(a), 0)
        k.rod(f"Walnut leg {i + 1}", "Walnut", foot, hub, 0.011, 0.016)
    k.cylinder("Brass hub", "Brass", 0, 0, 1.09, 1.15, 0.03, 0.026, segments=24)
    k.cylinder("Brass stem", "Brass", 0, 0, 1.15, 1.30, 0.008, segments=16, bevel=0.0)
    k.sphere("Bulb", "Warm bulb", 0, 0, 1.38, 0.04, 20, 12)
    k.lathe(
        "Drum shade",
        "Mustard wool",
        shell([(r, 1.26), (r, h - 0.002), (r - 0.002, h)], 0.004),
        segments=56,
        closed=True,
    )
    k.lathe(
        "Shade rim",
        "Brass",
        shell([(r - 0.004, 1.26), (r - 0.004, 1.268)], 0.006),
        segments=56,
        closed=True,
    )


def _canopy(k, h, finish):
    k.cylinder(
        "Ceiling canopy",
        finish,
        0,
        0,
        h - 0.03,
        h,
        0.055,
        0.06,
        segments=32,
        bevel=0.003,
    )


def pendant_globe_cluster(k, w, d, h):
    _canopy(k, h, "Brass")
    k.cylinder(
        "Brass stem", "Brass", 0, 0, 0.30, h - 0.03, 0.007, segments=16, bevel=0.0
    )
    k.sphere("Brass hub", "Brass", 0, 0, 0.30, 0.03, 24, 12)
    r = w / 2 - 0.06
    globes = [(0, 0, 0.07)] + [
        (
            r * math.cos(math.radians(45 * i)),
            r * math.sin(math.radians(45 * i)),
            0.17 + 0.07 * (i % 2),
        )
        for i in range(8)
    ]
    for i, (x, y, z) in enumerate(globes):
        if i:
            k.rod(f"Brass arm {i}", "Brass", (0, 0, 0.30), (x, y, z + 0.075), 0.005)
        k.cylinder(
            f"Brass socket {i + 1}",
            "Brass",
            x,
            y,
            z + 0.055,
            z + 0.085,
            0.014,
            segments=16,
            bevel=0.0,
        )
        k.sphere(
            f"Opal globe {i + 1}", "Opal glass", x, y, z, 0.06 if i else 0.07, 28, 14
        )


def pendant_dome(k, w, d, h):
    _canopy(k, h, "Black steel")
    r = w / 2
    k.cylinder(
        "Cord", "Black steel", 0, 0, 0.24, h - 0.03, 0.004, segments=12, bevel=0.0
    )
    k.lathe(
        "Steel dome",
        "Black steel",
        shell(
            [
                (r, 0.0),
                (r - 0.01, 0.04),
                (r * 0.8, 0.13),
                (r * 0.45, 0.2),
                (0.03, 0.235),
                (0.03, 0.27),
            ],
            0.003,
        ),
        segments=64,
        closed=True,
    )
    k.lathe(
        "Enamel reflector",
        "White lacquer",
        [(r - 0.006, 0.004), (r - 0.016, 0.04), (r * 0.8 - 0.006, 0.128), (0, 0.13)],
        segments=64,
    )
    k.sphere("Bulb", "Warm bulb", 0, 0, 0.1, 0.045, 24, 12)


def pendant_paper_lantern(k, w, d, h):
    _canopy(k, h, "Ash")
    r = w / 2
    profile = [
        (math.sin(math.pi * t / 12) * r * 0.985 + 0.004, 0.02 + 0.40 * t / 12)
        for t in range(13)
    ]
    profile[0] = (0.06, 0.02)
    profile[-1] = (0.06, 0.42)
    k.lathe(
        "Washi globe", "Washi paper", shell(profile, 0.002), segments=48, closed=True
    )
    for i in range(1, 12):
        rr, z = profile[i]
        k.lathe(
            f"Bamboo rib {i}",
            "Pale oak",
            [
                (rr - 0.001, z - 0.0025),
                (rr + 0.003, z - 0.0025),
                (rr + 0.003, z + 0.0025),
                (rr - 0.001, z + 0.0025),
            ],
            segments=48,
            closed=True,
        )
    k.cylinder("Bottom ring", "Ash", 0, 0, 0.0, 0.025, 0.065, segments=32, bevel=0.001)
    k.cylinder("Top ring", "Ash", 0, 0, 0.415, 0.44, 0.065, segments=32, bevel=0.001)
    k.cylinder(
        "Cord", "Charcoal linen", 0, 0, 0.44, h - 0.03, 0.004, segments=12, bevel=0.0
    )


def pendant_layered(k, w, d, h):
    _canopy(k, h, "White lacquer")
    r = w / 2
    k.cylinder(
        "Cord", "White lacquer", 0, 0, 0.36, h - 0.03, 0.004, segments=12, bevel=0.0
    )
    for i, (r0, r1, z0, z1) in enumerate(
        (
            (r, r * 0.72, 0.0, 0.08),
            (r * 0.74, r * 0.46, 0.1, 0.2),
            (r * 0.5, r * 0.18, 0.22, 0.36),
        )
    ):
        k.lathe(
            f"Shade tier {i + 1}",
            "White lacquer",
            shell([(r0, z0), (r1, z1)], 0.003),
            segments=64,
            closed=True,
        )
    k.lathe(
        "Inner diffuser",
        "Washi paper",
        [(0, 0.06), (r * 0.42, 0.06), (r * 0.3, 0.3), (0, 0.3)],
        segments=48,
    )


def pendant_brass_bell(k, w, d, h):
    _canopy(k, h, "Brass")
    r = w / 2
    k.cylinder("Brass rod", "Brass", 0, 0, 0.3, h - 0.03, 0.006, segments=16, bevel=0.0)
    k.lathe(
        "Brass bell",
        "Brass",
        shell(
            [
                (r, 0.0),
                (r * 0.93, 0.05),
                (r * 0.6, 0.16),
                (r * 0.3, 0.25),
                (0.035, 0.3),
            ],
            0.003,
        ),
        segments=64,
        closed=True,
    )
    k.lathe(
        "Opal diffuser",
        "Opal glass",
        [(0, 0.012), (r * 0.9, 0.012), (r * 0.9, 0.02), (0, 0.04)],
        segments=48,
    )


# concept_id -> (name, category, (w, d, h), builder)
PIECES = {
    "japandi-platform-bed": (
        "Japandi low platform bed",
        "bed",
        (1.6, 2.0, 0.6),
        bed_japandi,
    ),
    "scandi-oak-bed": (
        "Scandinavian oak bed with upholstered headboard",
        "bed",
        (1.6, 2.0, 0.6),
        bed_scandinavian,
    ),
    "walnut-tapered-bed": (
        "Mid-century walnut bed",
        "bed",
        (1.6, 2.0, 0.6),
        bed_mid_century,
    ),
    "channel-velvet-bed": (
        "Channel-tufted velvet bed",
        "bed",
        (1.6, 2.0, 0.6),
        bed_modern_classic,
    ),
    "steel-loft-bed": (
        "Steel loft bed with reclaimed oak",
        "bed",
        (1.6, 2.0, 0.6),
        bed_industrial,
    ),
    "japandi-low-sofa": ("Japandi low sofa", "sofa", (1.95, 0.84, 0.72), sofa_japandi),
    "scandi-linen-sofa": (
        "Scandinavian linen sofa",
        "sofa",
        (1.95, 0.84, 0.8),
        sofa_scandinavian,
    ),
    "mid-century-sofa": (
        "Mid-century track-arm sofa",
        "sofa",
        (1.95, 0.84, 0.8),
        sofa_mid_century,
    ),
    "japandi-ash-desk": ("Japandi ash desk", "desk", (1.4, 0.7, 0.75), desk_japandi),
    "walnut-writing-desk": (
        "Mid-century walnut writing desk",
        "desk",
        (1.4, 0.7, 0.75),
        desk_mid_century,
    ),
    "ebonised-writing-desk": (
        "Ebonised writing desk with brass",
        "desk",
        (1.4, 0.7, 0.75),
        desk_modern_classic,
    ),
    "shoji-shelving": (
        "Japandi shelving with shoji doors",
        "storage",
        (0.8, 0.4, 1.8),
        storage_japandi,
    ),
    "scandi-bookcase": (
        "Scandinavian bookcase",
        "storage",
        (0.8, 0.4, 1.8),
        storage_scandinavian,
    ),
    "classic-bookcase": (
        "Classic ebonised bookcase",
        "storage",
        (0.8, 0.4, 1.8),
        storage_modern_classic,
    ),
    "walnut-sideboard": (
        "Mid-century walnut sideboard",
        "storage",
        (1.6, 0.45, 0.75),
        sideboard_mid_century,
    ),
    "walnut-tripod-lamp": (
        "Walnut tripod floor lamp",
        "lamp",
        (0.4, 0.4, 1.6),
        floor_lamp_mid_century,
    ),
    "globe-cluster-pendant": (
        "Brass globe-cluster pendant",
        "lamp",
        (0.45, 0.45, 0.7),
        pendant_globe_cluster,
    ),
    "steel-dome-pendant": (
        "Black steel dome pendant",
        "lamp",
        (0.45, 0.45, 0.7),
        pendant_dome,
    ),
    "paper-lantern-pendant": (
        "Washi paper lantern",
        "lamp",
        (0.45, 0.45, 0.7),
        pendant_paper_lantern,
    ),
    "layered-pendant": (
        "Layered white pendant",
        "lamp",
        (0.45, 0.45, 0.7),
        pendant_layered,
    ),
    "brass-bell-pendant": (
        "Brass bell pendant",
        "lamp",
        (0.45, 0.45, 0.7),
        pendant_brass_bell,
    ),
}
VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Materials, UVs and normalisation (bpy)
# ---------------------------------------------------------------------------
def _release_files(asset_id):
    releases = json.loads((PACKS / "releases.json").read_text(encoding="utf-8"))
    release = next(r for r in releases if r["asset_id"] == asset_id)
    out = {}
    for f in release["files"]:
        if f["tier"] in ("low", "both"):
            out[f["role"]] = PACKS / "assets" / f"{f['sha256']}.{f['ext']}"
    return out


class Materials:
    def __init__(self, bpy, workdir):
        self.bpy, self.workdir, self.cache, self.textures = bpy, Path(workdir), {}, {}

    def _image(self, path, colorspace):
        img = self.bpy.data.images.load(str(path), check_existing=True)
        img.colorspace_settings.name = colorspace
        self.textures[path.stem] = path.name
        return img

    def _weave(self, asset_id, path):
        """A neutral grey weave map derived from a CC0 fabric scan (cached per asset)."""
        import numpy as np

        out = self.workdir / f"{asset_id.split(':')[1]}-weave.jpg"
        if not out.exists():
            src = self.bpy.data.images.load(str(path))
            size = 512
            src.scale(size, size)
            px = np.empty(size * size * 4, dtype=np.float32)
            src.pixels.foreach_get(px)
            px = px.reshape(-1, 4)
            lum = (
                px[:, :3] @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
            ).reshape(size, size)
            # High-pass: subtract a wrapped 33 px box blur so only the fine weave
            # survives; the scan's large tonal patches would otherwise tile as plaid.
            blur = lum.copy()
            for axis in (0, 1):
                acc = np.zeros_like(blur)
                for shift in range(-16, 17):
                    acc += np.roll(blur, shift, axis=axis)
                blur = acc / 33.0
            detail = (lum - blur).ravel()
            detail /= max(float(detail.std()), 1e-6)
            grey = np.clip(WEAVE_MEAN + detail * 0.06, 0, 1).astype(np.float32)
            img = self.bpy.data.images.new("weave", size, size)
            img.pixels.foreach_set(
                np.column_stack([grey, grey, grey, np.ones_like(grey)]).ravel()
            )
            img.filepath_raw = str(out)
            img.file_format = "JPEG"
            img.save()
            self.bpy.data.images.remove(img)
            self.bpy.data.images.remove(src)
        img = self.bpy.data.images.load(str(out), check_existing=True)
        img.colorspace_settings.name = "sRGB"
        return img

    def __call__(self, finish):
        if finish in self.cache:
            return self.cache[finish]
        spec = FINISHES[finish]
        mat = self.bpy.data.materials.new(finish)
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        mat["tile_m"] = spec.get("tile", 1.0)
        if spec["kind"] == "plain":
            color = hex_linear(spec["color"]) + (1,)
            bsdf.inputs["Base Color"].default_value = color
            mat.diffuse_color = color
            bsdf.inputs["Roughness"].default_value = spec["roughness"]
            bsdf.inputs["Metallic"].default_value = spec.get("metallic", 0.0)
        else:
            files = _release_files(spec["asset"])
            if spec["kind"] == "fabric":
                base = self._weave(spec["asset"], files["diffuse"])
                factor = [
                    min(1.0, c / srgb_to_linear(WEAVE_MEAN))
                    for c in hex_linear(spec["tint"])
                ]
            else:
                base = self._image(files["diffuse"], "sRGB")
                factor = list(hex_linear(spec["tint"]))
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = base
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
            mix.inputs[0].default_value = 1.0
            mix.inputs[7].default_value = factor + [1.0]
            nt.links.new(tex.outputs["Color"], mix.inputs[6])
            nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
            mat.diffuse_color = hex_linear(spec["tint"]) + (1,)
            rough = nt.nodes.new("ShaderNodeTexImage")
            rough.image = self._image(files["roughness"], "Non-Color")
            nt.links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
            normal_tex = nt.nodes.new("ShaderNodeTexImage")
            normal_tex.image = self._image(files["normal"], "Non-Color")
            normal = nt.nodes.new("ShaderNodeNormalMap")
            normal.inputs["Strength"].default_value = 0.8
            nt.links.new(normal_tex.outputs["Color"], normal.inputs["Color"])
            nt.links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
            bsdf.inputs["Metallic"].default_value = 0.0
        if spec.get("emission"):
            bsdf.inputs["Emission Color"].default_value = hex_linear(
                spec["emission"]
            ) + (1,)
            bsdf.inputs["Emission Strength"].default_value = 1.0
        self.cache[finish] = mat
        return mat


def _apply_modifiers(bpy, scene, parts):
    depsgraph = scene.view_layers[0].depsgraph
    depsgraph.update()
    for obj in parts:
        if not obj.modifiers and obj.matrix_basis.is_identity:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(
            evaluated, preserve_all_data_layers=True, depsgraph=depsgraph
        )
        mesh.transform(obj.matrix_basis)
        old = obj.data
        obj.modifiers.clear()
        obj.data = mesh
        obj.matrix_basis.identity()
        bpy.data.meshes.remove(old)


def _bounds(parts):
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for obj in parts:
        for v in obj.data.vertices:
            for i in range(3):
                lo[i] = min(lo[i], v.co[i])
                hi[i] = max(hi[i], v.co[i])
    return lo, hi


def _normalise(parts, wdh):
    """Scale and move the evaluated piece so its bounds are exactly W x D x H,
    floor-centred. The geometry must already be within 4% of the reservation."""
    from mathutils import Matrix

    lo, hi = _bounds(parts)
    target = (wdh[0], wdh[1], wdh[2])
    scale = [t / (high - low) for t, low, high in zip(target, lo, hi, strict=True)]
    if any(abs(s - 1) > 0.04 for s in scale):
        raise ValueError(
            f"Piece bounds {[high - low for low, high in zip(lo, hi)]} stray from {target}"
        )
    centre = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])
    matrix = Matrix.Diagonal((*scale, 1.0)) @ Matrix.Translation(
        (-centre[0], -centre[1], -centre[2])
    )
    for obj in parts:
        obj.data.transform(matrix)
        obj.data.update()
    return scale


def _box_uvs(obj):
    """Box-project UVs in metres / tile, with the wood grain along U."""
    mesh = obj.data
    tile = mesh.materials[0].get("tile_m", 1.0)
    grain = "xyz".index(obj["grain"])
    layer = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        n = poly.normal
        axis = max(range(3), key=lambda i: abs(n[i]))
        plane = [i for i in range(3) if i != axis]
        if grain in plane:
            u, v = grain, plane[1] if plane[0] == grain else plane[0]
        else:
            u, v = plane
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            layer.data[li].uv = (co[u] / tile, co[v] / tile)


def _studio(bpy, scene, wdh):
    from mathutils import Vector

    w, d, h = wdh
    size = max(w, d, h)
    stage = bpy.data.collections.new("Photography studio")
    scene.collection.children.link(stage)
    floor = bpy.data.meshes.new("Warm paper sweep")
    floor.from_pydata(
        [(-30, -30, -0.001), (30, -30, -0.001), (30, 30, -0.001), (-30, 30, -0.001)],
        [],
        [(0, 1, 2, 3)],
    )
    sweep = bpy.data.objects.new("Warm paper sweep", floor)
    stage.objects.link(sweep)
    paper = bpy.data.materials.new("Paper sweep")
    paper.use_nodes = True
    paper.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (
        hex_linear("E5DFD1") + (1,)
    )
    paper.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    floor.materials.append(paper)
    target = Vector((0, 0, h * 0.45))

    def aim(obj):
        obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()

    k = size / 0.83
    for name, position, power, area, color in (
        ("Window key", (-1.1, -1.25, 1.85), 83, 1.35, (1, 0.93, 0.84)),
        ("Soft fill", (1.35, -0.65, 1.1), 37, 1.0, (0.86, 0.93, 1)),
        ("Back rim", (0.4, 1.05, 1.66), 60, 0.85, (1, 0.92, 0.82)),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy = power * k * k
        light.shape, light.size, light.color = "DISK", area * k, color
        obj = bpy.data.objects.new(name, light)
        stage.objects.link(obj)
        obj.location = Vector(position) * k
        aim(obj)
    cameras = []
    aspect = 600 / 640
    for name, direction, extent in (
        ("Front", Vector((0, -1, 0.18)), max(w / aspect, h) * 1.18),
        (
            "Three-quarter",
            Vector((0.62, -0.78, 0.42)),
            max(math.hypot(w, d) / aspect, h + 0.4 * d) * 1.15,
        ),
    ):
        camera = bpy.data.cameras.new(name)
        camera.type = "ORTHO"
        camera.ortho_scale = extent
        camera.clip_end = 100
        obj = bpy.data.objects.new(name, camera)
        stage.objects.link(obj)
        obj.location = target + direction.normalized() * (4 * size + 2)
        aim(obj)
        cameras.append(obj)
    scene.world = bpy.data.worlds.new("Ambient studio")
    scene.world.color = (0.23, 0.23, 0.23)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 600, 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    return cameras


def author_piece(output_directory, concept_id):
    """Create a fresh scene for one piece and export a candidate into a new directory."""
    import bpy

    if tuple(bpy.app.version[:2]) < (5, 1):
        raise ValueError("Blender 5.1 or newer is required")
    name, category, wdh, builder = PIECES[concept_id]
    output = Path(output_directory).expanduser().resolve()
    output.mkdir(exist_ok=False)
    scene = bpy.data.scenes.new(f"{name} — {VERSION}")
    scene.unit_settings.system = "METRIC"
    collection = bpy.data.collections.new("ArchiMind piece")
    scene.collection.children.link(collection)
    workdir = Path(tempfile.mkdtemp(prefix="archimind-weave-"))
    materials = Materials(bpy, workdir)
    kit = Kit(bpy, collection, materials)
    builder(kit, *wdh)
    bpy.context.window.scene = scene
    _apply_modifiers(bpy, scene, kit.parts)
    scale = _normalise(kit.parts, wdh)
    for obj in kit.parts:
        _box_uvs(obj)
    scene["archimind_concept"] = concept_id
    scene["archimind_version"] = VERSION
    with bpy.context.temp_override(scene=scene, view_layer=scene.view_layers[0]):
        result = bpy.ops.export_scene.gltf(
            filepath=str(output / "piece.glb"),
            export_format="GLB",
            export_yup=True,
            use_active_scene=True,
            export_animations=False,
            export_cameras=False,
            export_lights=False,
            export_extras=False,
            export_image_format="JPEG",
            export_jpeg_quality=86,
            export_image_quality=86,
        )
        if result != {"FINISHED"}:
            raise RuntimeError("Blender GLB export did not finish")
        cameras = _studio(bpy, scene, wdh)
        for camera, filename in zip(
            cameras, ("front.png", "three-quarter.png"), strict=True
        ):
            scene.camera = camera
            scene.render.filepath = str(output / filename)
            result = bpy.ops.render.render(write_still=True, scene=scene.name)
            if result != {"FINISHED"}:
                raise RuntimeError("Blender preview render did not finish")
        scene.render.filepath = "//preview.png"
        # Pack every texture so the editable project reopens on any machine.
        for mat in materials.cache.values():
            for node in mat.node_tree.nodes:
                if (
                    node.type == "TEX_IMAGE"
                    and node.image
                    and not node.image.packed_file
                ):
                    node.image.pack()
        bpy.data.libraries.write(str(output / "piece.blend"), {scene}, compress=True)

    sources = sorted(
        {FINISHES[f]["asset"] for f in materials.cache if "asset" in FINISHES[f]}
    )
    metadata = {
        "schema_version": 2,
        "concept_id": concept_id,
        "version": VERSION,
        "name": name,
        "category": category,
        "dimensions_wdh_m": list(wdh),
        "blender_version": bpy.app.version_string,
        "attribution": ATTRIBUTION,
        "inputs": {
            "author_script_sha256": hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest(),
            "parts": [p.name for p in kit.parts],
            "finishes": {f: FINISHES[f] for f in sorted(materials.cache)},
            "cc0_texture_sources": {
                a: sorted(p.name for p in _release_files(a).values()) for a in sources
            },
            "normalising_scale_xyz": [round(s, 5) for s in scale],
            "blender_axes": "X width, -Y front, Z up",
            "glb_axes": "X width, +Z front, Y up",
        },
        "sha256": {
            f: hashlib.sha256((output / f).read_bytes()).hexdigest()
            for f in ("piece.blend", "piece.glb", "front.png", "three-quarter.png")
        },
    }
    (output / "authoring.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--output", type=Path, required=True)
    args.add_argument("--concept", choices=sorted(PIECES), required=True)
    selected = args.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else None
    )
    author_piece(selected.output, selected.concept)

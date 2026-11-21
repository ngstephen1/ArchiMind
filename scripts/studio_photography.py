"""Cycles material and camera treatments for the approved high-tier Town scene."""

import re


def attach_textile_detail():
    """Add cloth nap and woven relief to untextured authored fabrics in metre space."""
    import bpy

    treated = set()
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or "/furniture/" not in obj.get("saved_town_slot", ""):
            continue
        for mat in obj.data.materials:
            if not mat or not re.search(
                r"linen|upholstery|weave|velvet|wool", mat.name, re.I
            ):
                continue
            if not mat.use_nodes or mat.name in treated:
                continue
            tree = mat.node_tree
            shader = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if not shader:
                continue
            if tree.nodes.get("Woven surface relief"):
                treated.add(mat.name)
                continue
            if shader.inputs["Normal"].is_linked:
                continue
            # A stochastic fibre bump avoids regular moiré at the wide room cameras.
            coords = tree.nodes.new("ShaderNodeNewGeometry")
            fibre = tree.nodes.new("ShaderNodeTexNoise")
            fibre.inputs["Scale"].default_value = 450
            fibre.inputs["Detail"].default_value = 2
            tree.links.new(coords.outputs["Position"], fibre.inputs["Vector"])
            bump = tree.nodes.new("ShaderNodeBump")
            bump.name = "Woven surface relief"
            bump.inputs["Strength"].default_value = 0.28
            bump.inputs["Distance"].default_value = 0.0008
            tree.links.new(fibre.outputs["Fac"], bump.inputs["Height"])
            tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
            if not shader.inputs["Sheen Weight"].is_linked:
                shader.inputs["Sheen Weight"].default_value = 0.22
            treated.add(mat.name)
    return sorted(treated)


def daylight_exposure(room):
    """Meter each daytime interior by its ratio of glazing to floor area."""
    area = sum(w["width_m"] * w["height_m"] for w in room["windows"])
    ratio = area / (room["width_m"] * room["depth_m"])
    # In this scene exterior emitters scale with glazing area. Retain highlight
    # detail in large bays and raise the exposure of rooms with small apertures.
    return max(-0.9, min(1.2, 1.1 - ratio * 10))

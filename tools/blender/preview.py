"""Renders an HVYM asset with a state applied, as a player would show it.

    blender -b --factory-startup --python tools/blender/preview.py -- ASSET.gltf OUT.png '{"hat": 1}'

Imports the glTF, applies the properties' defaults overlaid with the given values through
the asset's sets and bindings (pointer bindings for morph weights, emissive colour and
visibility), and renders a three-quarter view. It's a check by eye of the format, not a
player: graphs, controls and animations aren't run.
"""

import json
import math
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
path, out = args[0], args[1]
values = json.loads(args[2]) if len(args) > 2 else {}

bpy.ops.wm.read_factory_settings(use_empty=True)
with open(path, encoding="utf-8") as f:
    g = json.load(f)
bpy.ops.import_scene.gltf(filepath=path)
ext = g["extensions"]["HVYM_asset"]
state = {p["name"]: values.get(p["name"], p["default"]) for p in ext["properties"]}
obj = lambda i: bpy.data.objects[g["nodes"][i]["name"]]
sets = {s["name"]: s for s in ext.get("sets", [])}


def material(i):
    """Material i, made from the glTF's factors when no face used it (the importer skips those)."""
    m = g["materials"][i]
    if m["name"] not in bpy.data.materials:
        new = bpy.data.materials.new(m["name"])
        new.use_nodes = True
        bsdf = new.node_tree.nodes["Principled BSDF"]
        pbr = m.get("pbrMetallicRoughness", {})
        bsdf.inputs["Base Color"].default_value = pbr.get("baseColorFactor", [1, 1, 1, 1])
        bsdf.inputs["Metallic"].default_value = pbr.get("metallicFactor", 1)
        bsdf.inputs["Roughness"].default_value = pbr.get("roughnessFactor", 1)
    return bpy.data.materials[m["name"]]


def show(o, visible):
    for x in [o, *o.children_recursive]:
        x.hide_render = not visible


# the file's own visibility (KHR_node_visibility), which the importer doesn't read
for i, n in enumerate(g["nodes"]):
    if not n.get("extensions", {}).get("KHR_node_visibility", {}).get("visible", True):
        show(obj(i), False)

for b in ext.get("bindings", []):
    v = state[b["property"]]
    if "set" in b:
        s = sets[b["set"]]
        if s["type"] == "nodes":
            for k, o in enumerate(s["options"]):
                show(obj(o), k == v)
        else:
            chosen = material(s["options"][v])
            for t in s["targets"]:
                mesh_name = g["meshes"][t["mesh"]]["name"]
                for o in bpy.data.objects:
                    if o.type == "MESH" and o.data.name == mesh_name:
                        o.material_slots[t["primitive"]].material = chosen
    elif "pointer" in b:
        parts = b["pointer"].strip("/").split("/")
        i = int(parts[1])
        if parts[0] == "nodes" and parts[2] == "weights":
            keys = obj(i).data.shape_keys.key_blocks
            keys[int(parts[3]) + 1].value = v  # key 0 is the basis
        elif parts[0] == "nodes" and parts[3:4] == ["KHR_node_visibility"]:
            show(obj(i), bool(v))
        elif parts[0] == "materials" and parts[2] == "emissiveFactor":
            bsdf = material(i).node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Emission Color"].default_value = (*v[:3], 1)

# a camera and three lights around what's visible
scene = bpy.context.scene
seen = [o for o in scene.objects if o.type == "MESH" and not o.hide_render]
pts = [o.matrix_world @ Vector(c) for o in seen for c in o.bound_box]
lo = Vector([min(p[k] for p in pts) for k in range(3)])
hi = Vector([max(p[k] for p in pts) for k in range(3)])
centre, size = (lo + hi) / 2, (hi - lo).length
cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
scene.collection.objects.link(cam)
cam.location = centre + Vector((0.9, -2.2, 0.6)).normalized() * size * 1.5
cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 50
scene.camera = cam
for name, power, at, colour in (("Key", 300, (2, -2, 3), (1, 0.93, 0.8)), ("Fill", 90, (-2.5, -1.5, 1.5), (0.8, 0.88, 1)),
                                ("Rim", 200, (0, 3, 2.5), (1, 1, 1))):
    light = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    light.data.energy, light.data.color, light.data.size = power, colour, 2
    light.location = centre + Vector(at)
    light.rotation_euler = (centre - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(light)
scene.world = bpy.data.worlds.new("World")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.04, 0.045, 0.05, 1)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 640, 640
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("HVYM-PREVIEW-OK", out, json.dumps(state))

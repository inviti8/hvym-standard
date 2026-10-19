"""Builds the example asset, Lantern Bot, in Blender and exports it with HVYM_asset.

    blender -b --factory-startup --python tools/blender/make_example.py -- examples/lantern-bot

Blender's exporter writes the plain glTF. This script then adds what the exporter can't
write yet: the HVYM_asset and HVYM_node_control extensions, KHR_node_visibility on the
hats, the second paint material, and a KHR_interactivity graph. That is the add-on's job
once it exists (docs/PLAN.md, phase 2). It writes lantern-bot.gltf + .bin and lantern-bot.glb.
"""

import json
import math
import os
import struct
import sys

import bpy

OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "examples/lantern-bot")
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 24


def material(name, color, emission=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.45
    if emission:
        bsdf.inputs["Emission Color"].default_value = emission
        bsdf.inputs["Emission Strength"].default_value = 1.0
    return m


def add(op, name, mat, parent=None, **kw):
    op(**kw)
    o = bpy.context.active_object
    o.name = o.data.name = name
    o.data.materials.append(mat)
    if parent:
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    bpy.ops.object.shade_smooth()
    return o


red = material("Paint_Red", (0.62, 0.06, 0.04, 1))
face = material("Face", (0.8, 0.8, 0.78, 1))
hat = material("Hat", (0.05, 0.05, 0.07, 1))
glow = material("Glow", (1, 0.8, 0.4, 1), emission=(1, 0.75, 0.3, 1))
button = material("Button", (0.9, 0.7, 0.1, 1))

body = add(bpy.ops.mesh.primitive_cube_add, "Body", red, size=1, location=(0, 0, 0.7))
body.scale = (0.55, 0.4, 0.6)
bpy.ops.object.transform_apply(scale=True)
dark = material("Dark", (0.02, 0.02, 0.025, 1))
# the body is 0.55 wide, 0.4 deep and 0.6 tall: its front face is at y = -0.2
head = add(bpy.ops.mesh.primitive_uv_sphere_add, "Head", face, body, radius=0.3, location=(0, 0, 1.3))
for side in (-1, 1):
    add(bpy.ops.mesh.primitive_uv_sphere_add, f"Eye_{'LR'[side > 0]}", dark, head, radius=0.045,
        location=(0.1 * side, -0.27, 1.38))
# the mouth: a thin bar whose ends lift into a smile (the Smile morph target, driven by mood)
mouth = add(bpy.ops.mesh.primitive_cube_add, "Mouth", dark, head, size=1, location=(0, -0.285, 1.2))
mouth.scale = (0.18, 0.03, 0.025)
bpy.ops.object.transform_apply(scale=True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.subdivide(number_cuts=8)
bpy.ops.object.mode_set(mode="OBJECT")
mouth.shape_key_add(name="Basis")
smile = mouth.shape_key_add(name="Smile")
for v in smile.data:
    x = v.co.x / 0.09  # -1 at one corner, 1 at the other
    v.co.z += 0.07 * x * x
    v.co.y -= 0.025 * x * x  # follows the head's curve
smile.value = 0.0  # mood's default: the file shows the defaults
add(bpy.ops.mesh.primitive_cone_add, "Hat_Cone", hat, head, radius1=0.22, depth=0.4, location=(0, 0, 1.75))
add(bpy.ops.mesh.primitive_cylinder_add, "Hat_Top", hat, head, radius=0.18, depth=0.35, location=(0, 0, 1.72))
arm = add(bpy.ops.mesh.primitive_cube_add, "Arm", face, body, size=1, location=(0.35, 0, 0.75))
arm.scale = (0.12, 0.12, 0.5)
bpy.ops.object.transform_apply(scale=True)
# the arm pivots at the shoulder
bpy.context.scene.cursor.location = (0.35, 0, 0.98)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
arm_l = add(bpy.ops.mesh.primitive_cube_add, "Arm_L", face, body, size=1, location=(-0.35, 0, 0.75))
arm_l.scale = (0.12, 0.12, 0.5)
bpy.ops.object.transform_apply(scale=True)
add(bpy.ops.mesh.primitive_cylinder_add, "ChestButton", button, body, radius=0.08, depth=0.04,
    location=(0, -0.21, 0.82), rotation=(math.pi / 2, 0, 0))
lantern = add(bpy.ops.mesh.primitive_uv_sphere_add, "Lantern", glow, body, radius=0.1, location=(-0.35, -0.14, 0.42))
add(bpy.ops.mesh.primitive_cube_add, "LampSwitch", button, body, size=0.08, location=(0, -0.22, 0.55))
bpy.ops.object.empty_add(location=(0.8, 0, 1.4))
anchor = bpy.context.active_object
anchor.name = "PanelAnchor"
anchor.parent = body


def animate(obj, name, path, keys, index=-1):
    """An action on obj named name, keyframing path at (frame, value) pairs."""
    obj.animation_data_create()
    act = bpy.data.actions.new(name)
    obj.animation_data.action = act
    for frame, value in keys:
        setattr(obj, path, value)
        obj.keyframe_insert(path, frame=frame, index=index)
    track = obj.animation_data.nla_tracks.new()
    track.name = name
    track.strips.new(name, int(keys[0][0]), act)
    obj.animation_data.action = None
    return act


animate(arm, "Wave", "rotation_euler", [(1, (0, 0, 0)), (7, (0, -2.4, 0)), (13, (0, -1.8, 0)),
                                        (19, (0, -2.4, 0)), (25, (0, 0, 0))])
animate(body, "Dance", "location", [(1, (0, 0, 0.7)), (7, (0, 0, 0.8)), (13, (0, 0, 0.7))])

path = os.path.join(OUT, "lantern-bot.gltf")
bpy.ops.export_scene.gltf(filepath=path, export_format="GLTF_SEPARATE", export_animation_mode="NLA_TRACKS",
                          export_morph=True, export_apply=False, export_yup=True)

# ---- what the add-on will write: the HVYM data and the parts Blender can't export yet
with open(path, encoding="utf-8") as f:
    g = json.load(f)
node = {n["name"]: i for i, n in enumerate(g["nodes"])}
mat = {m["name"]: i for i, m in enumerate(g["materials"])}
anim = {a["name"]: i for i, a in enumerate(g["animations"])}
mesh_of = lambda name: g["nodes"][node[name]]["mesh"]

# the second paint: the exporter drops materials no face uses
blue = json.loads(json.dumps(g["materials"][mat["Paint_Red"]]))
blue["name"] = "Paint_Blue"
blue["pbrMetallicRoughness"]["baseColorFactor"] = [0.04, 0.12, 0.62, 1]
g["materials"].append(blue)
mat["Paint_Blue"] = len(g["materials"]) - 1

# the hats: only the default, the cone, is visible
for name, visible in (("Hat_Cone", True), ("Hat_Top", False)):
    g["nodes"][node[name]].setdefault("extensions", {})["KHR_node_visibility"] = {"visible": visible}
g["nodes"][node["Lantern"]].setdefault("extensions", {})["KHR_node_visibility"] = {"visible": True}
g["nodes"][node["LampSwitch"]].setdefault("extensions", {})["HVYM_node_control"] = {
    "type": "toggle", "property": "lamp_on"}

props = [
    {"name": "name", "label": "Name", "type": "string", "default": "Lantern Bot", "maxLength": 24,
     "lifetime": "mint", "description": "Chosen by the buyer, then fixed."},
    {"name": "hat", "label": "Hat", "type": "choice", "options": ["Cone", "Top hat"], "default": 0,
     "lifetime": "mint"},
    {"name": "paint", "label": "Paint", "type": "choice", "options": ["Red", "Blue"], "default": 0,
     "lifetime": "mint"},
    {"name": "mood", "label": "Mood", "type": "float", "default": 0, "min": 0, "max": 1, "lifetime": "view"},
    {"name": "lamp", "label": "Lamp colour", "type": "color", "default": [1, 0.75, 0.3, 1], "lifetime": "view"},
    {"name": "lamp_on", "label": "Lamp", "type": "bool", "default": True, "lifetime": "view"},
    {"name": "dance", "label": "Dance", "type": "bool", "default": False, "lifetime": "view"},
    {"name": "xp", "label": "Experience", "type": "int", "default": 0, "min": 0, "max": 1000000,
     "lifetime": "live", "change": "increase", "by": ["delegate"],
     "description": "Only ever goes up, and only a game the creator authorises can raise it."},
    {"name": "durability", "label": "Durability", "type": "int", "default": 100, "min": 0, "max": 100,
     "lifetime": "live", "change": "decrease", "amount": 1, "by": ["delegate"]},
    {"name": "series", "label": "Series", "type": "int", "default": 1, "min": 1, "max": 1, "lifetime": "constant"},
]
xp = [p["name"] for p in props].index("xp")
body_mesh = mesh_of("Body")
g.setdefault("extensions", {})["HVYM_asset"] = {
    "specVersion": "0.1",
    "kind": "character",
    "title": "Lantern Bot",
    "creator": {"name": "HEAVYMETA"},
    "tags": ["example", "robot"],
    "properties": props,
    "sets": [
        {"name": "hat", "type": "nodes", "options": [node["Hat_Cone"], node["Hat_Top"]]},
        {"name": "paint", "type": "materials", "options": [mat["Paint_Red"], mat["Paint_Blue"]],
         "targets": [{"mesh": body_mesh, "primitive": 0}]},
    ],
    "bindings": [
        {"property": "hat", "set": "hat"},
        {"property": "paint", "set": "paint"},
        {"property": "mood", "pointer": f"/nodes/{node['Mouth']}/weights/0"},
        {"property": "lamp", "pointer": f"/materials/{mat['Glow']}/emissiveFactor"},
        {"property": "lamp_on", "pointer": f"/nodes/{node['Lantern']}/extensions/KHR_node_visibility/visible"},
        {"property": "dance", "animation": anim["Dance"], "drive": "play", "loop": "repeat"},
    ],
    "panels": [{
        "name": "Lantern Bot", "anchor": node["PanelAnchor"], "align": "left",
        "colors": {"primary": [0.04, 0.48, 0.34, 1], "text": [1, 1, 1, 1]},
        "groups": [
            {"label": "Look", "properties": ["hat", "paint", "mood", "lamp", "lamp_on", "dance"]},
            {"label": "Stats", "properties": ["xp", "durability", "series"]},
            {"label": "Name", "properties": ["name"]},
        ],
    }],
}


def duration(a):
    """An animation's length in seconds: the latest key time of its samplers."""
    return max(g["accessors"][s["input"]]["max"][0] for s in g["animations"][a]["samplers"])


wave = anim["Wave"]
start = [{"type": 0, "value": [0]}]
# press the chest button (core KHR_node_selectability) or gain experience: the bot waves
g["extensions"]["KHR_interactivity"] = {"graphs": [{
    "types": [{"signature": "float"}, {"signature": "int"}, {"signature": "ref"}, {"signature": "float3"}],
    "declarations": [
        {"op": "event/onSelect", "extension": "KHR_node_selectability",
         "outputValueSockets": {"selectedNode": {"type": 2}, "controllerIndex": {"type": 1},
                                "selectionPoint": {"type": 3}, "selectionRayOrigin": {"type": 3}}},
        {"op": "hvym/property/onChange", "extension": "HVYM_asset",
         "outputValueSockets": {"value": {"type": 0}}},
        {"op": "animation/start"},
    ],
    "nodes": [
        {"declaration": 0, "configuration": {"nodeIndex": {"value": [node["ChestButton"]]}},
         "flows": {"out": {"node": 2}}},
        {"declaration": 1, "configuration": {"property": {"value": [xp]}}, "flows": {"out": {"node": 2}}},
        {"declaration": 2, "values": {
            "animation": {"type": 1, "value": [wave]},
            "startTime": start[0],
            "endTime": {"type": 0, "value": [round(duration(wave), 4)]},
            "speed": {"type": 0, "value": [1]}}},
    ],
}]}
used = g.setdefault("extensionsUsed", [])
for e in ("HVYM_asset", "HVYM_node_control", "KHR_node_visibility", "KHR_node_selectability", "KHR_interactivity"):
    if e not in used:
        used.append(e)

with open(path, "w", encoding="utf-8", newline="\n") as f:
    json.dump(g, f, indent=1)
    f.write("\n")

# the same as one .glb
with open(os.path.join(OUT, "lantern-bot.bin"), "rb") as f:
    binary = f.read()
packed = json.loads(json.dumps(g))
del packed["buffers"][0]["uri"]
text = json.dumps(packed, separators=(",", ":")).encode()
text += b" " * (-len(text) % 4)
binary += b"\0" * (-len(binary) % 4)
with open(os.path.join(OUT, "lantern-bot.glb"), "wb") as f:
    f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(text) + 8 + len(binary)))
    f.write(struct.pack("<II", len(text), 0x4E4F534A) + text)
    f.write(struct.pack("<II", len(binary), 0x004E4942) + binary)
print("HVYM-EXAMPLE-OK", OUT)

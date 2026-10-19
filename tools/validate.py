"""Validates HVYM_asset assets against the spec (spec/HVYM_asset.md, "Validation").

    python tools/validate.py examples/lantern-bot/lantern-bot.gltf [more files...]

Checks the extension objects against the JSON Schemas in spec/schema, then the rules a
schema can't express: unique names, ranges, indices into the glTF, binding and control
type rules, set defaults, and the HVYM graph operations. Prints each problem and exits 1
if there are any. Needs `jsonschema` (requirements-dev.txt).
"""

import json
import pathlib
import re
import struct
import sys

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "spec" / "schema"
EXT = "HVYM_asset"
CONTROL = "HVYM_node_control"
VISIBILITY = "KHR_node_visibility"
INT_LIMIT = 2**53 - 1
HVYM_OPS = {"hvym/property/get", "hvym/property/set", "hvym/property/onChange"}

# the Object Model targets version 0.1 allows, and their types
POINTERS = [
    (r"/nodes/(\d+)/(translation|scale)", "float3", "nodes"),
    (r"/nodes/(\d+)/rotation", "float4", "nodes"),
    (r"/nodes/(\d+)/weights/(\d+)", "float", "nodes"),
    (r"/meshes/(\d+)/weights/(\d+)", "float", "meshes"),
    (r"/nodes/(\d+)/extensions/KHR_node_visibility/visible", "bool", "nodes"),
    (r"/materials/(\d+)/pbrMetallicRoughness/baseColorFactor", "float4", "materials"),
    (r"/materials/(\d+)/pbrMetallicRoughness/(metallicFactor|roughnessFactor)", "float", "materials"),
    (r"/materials/(\d+)/emissiveFactor", "float3", "materials"),
    (r"/materials/(\d+)/extensions/KHR_materials_emissive_strength/emissiveStrength", "float", "materials"),
    (r"/materials/(\d+)/alphaCutoff", "float", "materials"),
]
WIDTH = {"float3": 3, "float4": 4}


def load_gltf(path):
    """The glTF JSON of a .gltf or a .glb file."""
    data = pathlib.Path(path).read_bytes()
    if data[:4] == b"glTF":
        length, kind = struct.unpack_from("<II", data, 12)
        if kind != 0x4E4F534A:
            raise ValueError("the GLB's first chunk isn't JSON")
        return json.loads(data[20:20 + length])
    return json.loads(data)


def validators():
    registry = Registry()
    for f in SCHEMAS.glob("*.schema.json"):
        schema = json.loads(f.read_text(encoding="utf-8"))
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    get = lambda name: Draft202012Validator(registry[name].contents, registry=registry)
    return get("glTF.HVYM_asset.schema.json"), get("node.HVYM_node_control.schema.json")


def check(gltf):
    """Every problem with the asset, as strings. Empty means valid."""
    errors = []
    err = errors.append
    asset_schema, control_schema = validators()

    ext = gltf.get("extensions", {}).get(EXT)
    if ext is None:
        return [f"no {EXT} extension at the root"]
    for e in asset_schema.iter_errors(ext):
        err(f"schema: {EXT}/{'/'.join(map(str, e.absolute_path))}: {e.message}")
    controls = {}
    for i, node in enumerate(gltf.get("nodes", [])):
        c = node.get("extensions", {}).get(CONTROL)
        if c is not None:
            controls[i] = c
            for e in control_schema.iter_errors(c):
                err(f"schema: nodes/{i}/{CONTROL}/{'/'.join(map(str, e.absolute_path))}: {e.message}")
    if errors:
        return errors  # the rest assumes the shapes are right

    used = gltf.get("extensionsUsed", [])
    required = gltf.get("extensionsRequired", [])
    for name, present in ((EXT, True), (CONTROL, bool(controls))):
        if present and name not in used:
            err(f"{name} isn't in extensionsUsed")
        if name in required:
            err(f"{name} mustn't be in extensionsRequired")

    nodes = gltf.get("nodes", [])
    meshes = gltf.get("meshes", [])
    materials = gltf.get("materials", [])
    animations = gltf.get("animations", [])
    counts = {"nodes": len(nodes), "meshes": len(meshes), "materials": len(materials)}

    def exists(kind, i, where):
        if not 0 <= i < counts[kind]:
            err(f"{where}: {kind[:-1]} {i} doesn't exist")
            return False
        return True

    # properties
    props = {}
    for i, p in enumerate(ext["properties"]):
        where = f"properties/{i} ({p['name']})"
        if p["name"] in props:
            err(f"{where}: the name is used twice")
        props[p["name"]] = p
        t, d = p["type"], p["default"]
        if t in ("int", "float"):
            lo, hi = p["min"], p["max"]
            if not lo <= d <= hi:
                err(f"{where}: default {d} isn't within [{lo}, {hi}]")
            if t == "int" and max(abs(lo), abs(hi)) > INT_LIMIT:
                err(f"{where}: the range is beyond ±(2^53 - 1)")
        elif "min" in p or "max" in p:
            err(f"{where}: min and max are only for int and float")
        if t == "choice" and not d < len(p["options"]):
            err(f"{where}: default {d} isn't one of the {len(p['options'])} options")
        if t != "choice" and "options" in p:
            err(f"{where}: options are only for choice")
        if t == "string" and len(d.encode("utf-8")) > p.get("maxLength", 64):
            err(f"{where}: the default is longer than maxLength")
        if t != "string" and "maxLength" in p:
            err(f"{where}: maxLength is only for string")
        if "decimals" in p and not (t == "float" and p["lifetime"] in ("mint", "live")):
            err(f"{where}: decimals is only for stored floats")
        change = p.get("change")
        if change in ("increase", "decrease", "step") and t not in ("int", "float"):
            err(f"{where}: {change} applies only to int and float")
        if "amount" in p and change not in ("increase", "decrease", "step"):
            err(f"{where}: amount needs change increase, decrease or step")
        if "amount" in p and t in ("int", "float") and p["amount"] > p["max"] - p["min"]:
            err(f"{where}: amount {p['amount']} is larger than the whole range")
    def prop(name, where):
        if name not in props:
            err(f"{where}: no property named {name!r}")
        return props.get(name)

    # bindings
    set_driver = {}
    for i, b in enumerate(ext.get("bindings", [])):
        where = f"bindings/{i}"
        p = prop(b["property"], where)
        if p is None:
            continue
        t = p["type"]
        m = b.get("map", {})
        if "from" in m and m["from"][0] == m["from"][1]:
            err(f"{where}: map.from is an empty range")
        if "pointer" in b:
            target = pointer_type(b["pointer"], gltf, where, err, exists)
            if target is None:
                continue
            to = m.get("to")
            numbers = to is None or all(isinstance(v, (int, float)) for v in to)
            if t in ("int", "float") and target == "float":
                if not numbers:
                    err(f"{where}: map.to must be two numbers for a float target")
            elif t in ("int", "float") and target in WIDTH:
                if to is None or numbers or any(len(v) != WIDTH[target] for v in to):
                    err(f"{where}: a {t} driving a {target} needs map.to as two {target} values")
            elif t == "bool" and target == "bool":
                if m:
                    err(f"{where}: a bool driving a bool takes no map")
            elif t == "bool" and target == "float":
                if not numbers or "from" in m:
                    err(f"{where}: a bool driving a float takes only map.to, two numbers")
            elif t == "color" and target in WIDTH:
                if m:
                    err(f"{where}: a color takes no map")
            else:
                err(f"{where}: a {t} property can't drive a {target} target")
                continue
            # the fallback rule: the plain file shows the property's default
            want, have = bound_value(p, b), file_value(gltf, b["pointer"])
            if not close(want, have):
                err(f"{where}: {b['pointer']} is {have} in the file, but {p['name']}'s default gives {want}")
        elif "set" in b:
            sets = {s["name"]: s for s in ext.get("sets", [])}
            s = sets.get(b["set"])
            if s is None:
                err(f"{where}: no set named {b['set']!r}")
                continue
            if b["set"] in set_driver:
                err(f"{where}: set {b['set']!r} is already driven by bindings/{set_driver[b['set']]}")
            set_driver[b["set"]] = i
            n = len(s["options"])
            if t == "choice":
                if len(p["options"]) != n:
                    err(f"{where}: {p['name']} has {len(p['options'])} options but set {s['name']!r} has {n}")
            elif t == "int":
                if p["min"] < 0 or p["max"] >= n:
                    err(f"{where}: {p['name']}'s range [{p['min']}, {p['max']}] isn't within the set's options 0-{n - 1}")
            else:
                err(f"{where}: a set is driven by a choice or an int, not a {t}")
        else:
            if not b["animation"] < len(animations):
                err(f"{where}: animation {b['animation']} doesn't exist")
            if b["drive"] == "play" and t != "bool":
                err(f"{where}: drive play needs a bool, not a {t}")
            if b["drive"] in ("weight", "time") and t not in ("float", "int"):
                err(f"{where}: drive {b['drive']} needs a float or an int, not a {t}")
            if b["drive"] == "play" and m:
                err(f"{where}: drive play takes no map")

    # sets, and their defaults in the file
    bindings = ext.get("bindings", [])
    names = set()
    for i, s in enumerate(ext.get("sets", [])):
        where = f"sets/{i} ({s['name']})"
        if s["name"] in names:
            err(f"{where}: the name is used twice")
        names.add(s["name"])
        kind = "nodes" if s["type"] == "nodes" else "materials"
        if not all(exists(kind, o, where) for o in s["options"]):
            continue
        default = 0
        if s["name"] in set_driver:
            p = props.get(bindings[set_driver[s["name"]]]["property"])
            if p is not None and isinstance(p["default"], int) and 0 <= p["default"] < len(s["options"]):
                default = p["default"]
        if s["type"] == "nodes":
            if VISIBILITY not in used:
                err(f"{where}: a nodes set needs {VISIBILITY} in extensionsUsed")
            for k, o in enumerate(s["options"]):
                vis = nodes[o].get("extensions", {}).get(VISIBILITY)
                if vis is None:
                    err(f"{where}: option node {o} has no {VISIBILITY}")
                elif vis.get("visible", True) != (k == default):
                    err(f"{where}: option node {o} should be {'visible' if k == default else 'hidden'} in the file")
        else:
            for t in s["targets"]:
                if not exists("meshes", t["mesh"], where):
                    continue
                prims = meshes[t["mesh"]].get("primitives", [])
                if not t["primitive"] < len(prims):
                    err(f"{where}: mesh {t['mesh']} has no primitive {t['primitive']}")
                elif prims[t["primitive"]].get("material") != s["options"][default]:
                    err(f"{where}: mesh {t['mesh']} primitive {t['primitive']} should use the default option, material {s['options'][default]}")

    # controls
    fits = {"toggle": ("bool",), "slider": ("int", "float"), "selector": ("choice", "int"), "text": ("string",)}
    for n, c in controls.items():
        where = f"nodes/{n}/{CONTROL}"
        if c["type"] == "button":
            if "property" in c:
                err(f"{where}: a button sends an event and takes no property")
            continue
        p = prop(c["property"], where)
        if p is not None and p["type"] not in fits[c["type"]]:
            err(f"{where}: a {c['type']} can't change a {p['type']} property")
        if c["type"] == "slider":
            handle = c.get("handle")
            if handle is None:
                if not nodes[n].get("children"):
                    err(f"{where}: a slider needs a handle node or a child")
            else:
                exists("nodes", handle, where)
        for key in ("handle", "axis", "length"):
            if key in c and c["type"] != "slider":
                err(f"{where}: {key} is only for a slider")
        if "wrap" in c and c["type"] != "selector":
            err(f"{where}: wrap is only for a selector")

    # panels
    for i, panel in enumerate(ext.get("panels", [])):
        where = f"panels/{i}"
        if "anchor" in panel:
            exists("nodes", panel["anchor"], where)
        for g in panel["groups"]:
            for name in g["properties"]:
                prop(name, where)

    # graphs: the HVYM operations' configuration and sockets
    graphs = gltf.get("extensions", {}).get("KHR_interactivity", {}).get("graphs", [])
    for gi, g in enumerate(graphs):
        types = [t.get("signature") for t in g.get("types", [])]
        decls = g.get("declarations", [])
        for di, d in enumerate(decls):
            if d.get("extension") != EXT:
                continue
            where = f"KHR_interactivity/graphs/{gi}/declarations/{di}"
            if d.get("op") not in HVYM_OPS:
                err(f"{where}: {d.get('op')!r} isn't an {EXT} operation")
                continue
            sockets = {**d.get("inputValueSockets", {}), **d.get("outputValueSockets", {})}
            if set(sockets) != {"value"} or not _is_float(types, sockets["value"]):
                err(f"{where}: {d['op']} has one value socket, value: float")
        for ni, node in enumerate(g.get("nodes", [])):
            d = node.get("declaration")
            if not isinstance(d, int) or not 0 <= d < len(decls) or decls[d].get("extension") != EXT:
                continue
            where = f"KHR_interactivity/graphs/{gi}/nodes/{ni}"
            value = node.get("configuration", {}).get("property", {}).get("value")
            if not (isinstance(value, list) and len(value) == 1 and isinstance(value[0], int)):
                err(f"{where}: needs configuration property: {{value: [index]}}")
                continue
            k = value[0]
            if not 0 <= k < len(ext["properties"]):
                err(f"{where}: property {k} doesn't exist")
            elif ext["properties"][k]["type"] in ("color", "string"):
                err(f"{where}: {ext['properties'][k]['name']} is a {ext['properties'][k]['type']}, which graphs can't carry")
    return errors


def bound_value(p, b):
    """What a binding sets its pointer to for the property's default."""
    d, m = p["default"], b.get("map", {})
    if p["type"] == "color":
        return d
    if p["type"] == "bool":
        if "to" not in m:
            return d  # compares equal to 1 / 0 for a float target
        return m["to"][1] if d else m["to"][0]
    lo, hi = m.get("from", [p["min"], p["max"]])
    if "to" not in m:
        return d
    f = min(max((d - lo) / (hi - lo), 0.0), 1.0)
    a, z = m["to"]
    if isinstance(a, (int, float)):
        return a + (z - a) * f
    # linear, also for rotations: exact at the ends, which is where defaults usually sit
    return [x + (y - x) * f for x, y in zip(a, z)]


def file_value(gltf, pointer):
    """The value at a pointer in the plain file, with glTF's defaults."""
    parts = pointer.strip("/").split("/")
    root, i = parts[0], int(parts[1])
    obj = gltf[root][i]
    if root == "nodes" and parts[2] in ("translation", "rotation", "scale"):
        return obj.get(parts[2], {"translation": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]}[parts[2]])
    if parts[2] == "weights":
        w = int(parts[3])
        weights = obj.get("weights") or (gltf["meshes"][obj["mesh"]].get("weights") if root == "nodes" else None)
        return weights[w] if weights else 0.0
    if parts[2] == "extensions" and parts[3] == VISIBILITY:
        return obj.get("extensions", {}).get(VISIBILITY, {}).get("visible", True)
    if parts[2] == "pbrMetallicRoughness":
        defaults = {"baseColorFactor": [1, 1, 1, 1], "metallicFactor": 1.0, "roughnessFactor": 1.0}
        return obj.get("pbrMetallicRoughness", {}).get(parts[3], defaults[parts[3]])
    if parts[2] == "emissiveFactor":
        return obj.get("emissiveFactor", [0, 0, 0])
    if parts[2] == "alphaCutoff":
        return obj.get("alphaCutoff", 0.5)
    return obj.get("extensions", {}).get(parts[3], {}).get(parts[4], 1.0)  # emissiveStrength


def close(a, b, tol=1e-4):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, list):
        n = len(b) if isinstance(b, list) else 0
        return isinstance(b, list) and all(abs(x - y) <= tol for x, y in zip(a[:n], b))
    return isinstance(b, (int, float)) and abs(a - b) <= tol


def _is_float(types, socket):
    t = socket.get("type") if isinstance(socket, dict) else None
    return isinstance(t, int) and 0 <= t < len(types) and types[t] == "float"


def pointer_type(pointer, gltf, where, err, exists):
    """The target type of an allowed pointer, or None (reported) if it isn't allowed or valid."""
    for pattern, kind, root in POINTERS:
        m = re.fullmatch(pattern, pointer)
        if not m:
            continue
        i = int(m.group(1))
        if not exists(root, i, where):
            return None
        if "/weights/" in pointer:
            if root == "meshes":
                mesh = gltf["meshes"][i]
            else:
                mesh = gltf["meshes"][gltf["nodes"][i]["mesh"]] if "mesh" in gltf["nodes"][i] else None
            targets = len(mesh["primitives"][0].get("targets", [])) if mesh else 0
            if not int(m.group(2)) < targets:
                err(f"{where}: {pointer}: the mesh has {targets} morph targets")
                return None
        if VISIBILITY in pointer and VISIBILITY not in gltf.get("extensionsUsed", []):
            err(f"{where}: {pointer} needs {VISIBILITY} in extensionsUsed")
        return kind
    err(f"{where}: {pointer} isn't a pointer version 0.1 allows")
    return None


def main(paths):
    bad = 0
    for path in paths:
        problems = check(load_gltf(path))
        print(f"{path}: {'valid' if not problems else f'{len(problems)} problem(s)'}")
        for p in problems:
            print("  -", p)
        bad += bool(problems)
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1:]))

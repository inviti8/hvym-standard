"""The validator accepts the example and catches each kind of mistake.

    python -m unittest discover -s tests

Each case breaks one thing in a copy of the example asset, and checks the validator reports
it. The example itself is built by tools/blender/make_example.py.
"""

import copy
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import validate  # noqa: E402

EXAMPLE = ROOT / "examples" / "lantern-bot" / "lantern-bot.gltf"
BASE = validate.load_gltf(EXAMPLE)


def ext(g):
    return g["extensions"]["HVYM_asset"]


def prop(g, name):
    return next(p for p in ext(g)["properties"] if p["name"] == name)


def node(g, name):
    return next(i for i, n in enumerate(g["nodes"]) if n["name"] == name)


class Example(unittest.TestCase):
    def test_gltf_and_glb_are_valid(self):
        self.assertEqual(validate.check(BASE), [])
        self.assertEqual(validate.check(validate.load_gltf(EXAMPLE.with_suffix(".glb"))), [])

    def test_glb_matches_gltf(self):
        glb = validate.load_gltf(EXAMPLE.with_suffix(".glb"))
        self.assertEqual(glb["extensions"], BASE["extensions"])


class Mistakes(unittest.TestCase):
    def broken(self, change, expect):
        g = copy.deepcopy(BASE)
        change(g)
        problems = validate.check(g)
        self.assertTrue(any(expect in p for p in problems), f"wanted {expect!r} in {problems}")

    def test_schema(self):
        self.broken(lambda g: ext(g).pop("specVersion"), "'specVersion' is a required property")
        self.broken(lambda g: prop(g, "mood").update(type="number"), "schema: HVYM_asset/properties/3/type")
        self.broken(lambda g: prop(g, "xp").update(name="XP"), "does not match")
        self.broken(lambda g: prop(g, "mood").update(change="set"), "schema")  # change only for live
        self.broken(lambda g: prop(g, "xp").pop("by"), "schema")
        self.broken(lambda g: prop(g, "durability").update(amount=0.5), "schema")  # an int's amount is whole

    def test_extensions_used(self):
        self.broken(lambda g: g["extensionsUsed"].remove("HVYM_asset"), "HVYM_asset isn't in extensionsUsed")
        self.broken(lambda g: g["extensionsUsed"].remove("HVYM_node_control"), "HVYM_node_control isn't in")
        self.broken(lambda g: g.setdefault("extensionsRequired", []).append("HVYM_asset"), "mustn't be in extensionsRequired")

    def test_properties(self):
        self.broken(lambda g: prop(g, "mood").update(name="xp"), "the name is used twice")
        self.broken(lambda g: prop(g, "durability").update(default=101), "isn't within [0, 100]")
        self.broken(lambda g: prop(g, "hat").update(default=2), "isn't one of the 2 options")
        self.broken(lambda g: prop(g, "name").update(default="A" * 25), "longer than maxLength")
        self.broken(lambda g: prop(g, "name").update(lifetime="live", change="increase", by=["owner"]),
                    "increase applies only to int and float")
        self.broken(lambda g: prop(g, "xp").update(change="set", amount=1), "amount needs change")
        self.broken(lambda g: prop(g, "durability").update(amount=500), "larger than the whole range")
        self.broken(lambda g: prop(g, "mood").update(decimals=2), "decimals is only for stored floats")

    def test_bindings(self):
        b = lambda g, k: ext(g)["bindings"][k]
        mouth = node(BASE, "Mouth")
        self.broken(lambda g: b(g, 2).update(property="nope"), "no property named 'nope'")
        self.broken(lambda g: b(g, 2).update(pointer=f"/nodes/{mouth}/weights/3"), "the mesh has 1 morph targets")
        self.broken(lambda g: b(g, 2).update(pointer=f"/nodes/{node(BASE, 'Head')}/weights/0"), "the mesh has 0 morph targets")
        self.broken(lambda g: b(g, 2).update(pointer="/nodes/99/weights/0"), "node 99 doesn't exist")
        self.broken(lambda g: b(g, 2).update(pointer="/nodes/4/matrix"), "isn't a pointer version 0.1 allows")
        self.broken(lambda g: b(g, 2).update(pointer="/nodes/4/translation"), "needs map.to as two float3 values")
        self.broken(lambda g: b(g, 4).update(property="mood"), "a float property can't drive a bool target")
        self.broken(lambda g: b(g, 3).update(map={"to": [0, 1]}), "a color takes no map")
        self.broken(lambda g: b(g, 0).update(set="paint"), "already driven")
        self.broken(lambda g: b(g, 0).update(property="mood"), "a set is driven by a choice or an int")
        self.broken(lambda g: prop(g, "hat")["options"].append("Crown"), "has 3 options but set 'hat' has 2")
        self.broken(lambda g: b(g, 5).update(property="mood"), "drive play needs a bool")
        self.broken(lambda g: b(g, 5).update(animation=9), "animation 9 doesn't exist")
        self.broken(lambda g: b(g, 5).update(pointer="/nodes/0/scale"), "schema")  # two targets

    def test_fallback(self):
        # the plain file must show the defaults
        self.broken(lambda g: prop(g, "mood").update(default=0.5), "mood's default gives 0.5")
        self.broken(lambda g: prop(g, "lamp_on").update(default=False), "lamp_on's default gives False")
        glow = next(i for i, m in enumerate(BASE["materials"]) if m["name"] == "Glow")
        self.broken(lambda g: g["materials"][glow].update(emissiveFactor=[0, 0, 0]), "lamp's default gives")

    def test_sets(self):
        cone, top = node(BASE, "Hat_Cone"), node(BASE, "Hat_Top")
        self.broken(lambda g: g["nodes"][top]["extensions"].pop("KHR_node_visibility"), "has no KHR_node_visibility")
        self.broken(lambda g: g["nodes"][top]["extensions"]["KHR_node_visibility"].update(visible=True),
                    "should be hidden in the file")
        self.broken(lambda g: prop(g, "hat").update(default=1), f"option node {cone} should be hidden")
        self.broken(lambda g: prop(g, "paint").update(default=1), "should use the default option")
        self.broken(lambda g: ext(g)["sets"][1]["targets"][0].update(primitive=4), "has no primitive 4")
        self.broken(lambda g: ext(g)["sets"][0]["options"].append(99), "node 99 doesn't exist")
        self.broken(lambda g: ext(g)["sets"][1].update(name="hat"), "the name is used twice")
        self.broken(lambda g: ext(g)["sets"][0].update(targets=[{"mesh": 0, "primitive": 0}]), "schema")

    def test_controls(self):
        switch = node(BASE, "LampSwitch")
        c = lambda g: g["nodes"][switch]["extensions"]["HVYM_node_control"]
        self.broken(lambda g: c(g).update(property="mood"), "a toggle can't change a float property")
        self.broken(lambda g: c(g).update(type="slider", property="mood"), "a slider needs a handle node or a child")
        self.broken(lambda g: c(g).update(type="button"), "schema")  # a button needs an event
        self.broken(lambda g: c(g).update(axis="y"), "axis is only for a slider")
        self.broken(lambda g: c(g).update(property="gone"), "no property named 'gone'")

    def test_panels(self):
        self.broken(lambda g: ext(g)["panels"][0]["groups"][0]["properties"].append("gone"), "no property named 'gone'")
        self.broken(lambda g: ext(g)["panels"][0].update(anchor=99), "node 99 doesn't exist")

    def test_graphs(self):
        graph = lambda g: g["extensions"]["KHR_interactivity"]["graphs"][0]
        self.broken(lambda g: graph(g)["nodes"][1]["configuration"]["property"].update(value=[99]), "property 99 doesn't exist")
        self.broken(lambda g: graph(g)["nodes"][1]["configuration"]["property"].update(value=[0]),
                    "name is a string, which graphs can't carry")
        self.broken(lambda g: graph(g)["nodes"][1].pop("configuration"), "needs configuration property")
        self.broken(lambda g: graph(g)["declarations"][1].update(op="hvym/property/explode"), "isn't an HVYM_asset operation")
        self.broken(lambda g: graph(g)["declarations"][1]["outputValueSockets"]["value"].update(type=1), "value: float")


if __name__ == "__main__":
    unittest.main()

# Heavymeta Standard

**Programmable 3D assets.** A character, a prop or an object that carries its own properties, the
rules for how they may change, and its own behaviour, in one open glTF file. Copies can be owned,
with each copy's state kept on a public ledger under those same rules.

> An artist designs a character in Blender. Its buyer names it. Its mood drives its face. Its
> experience only ever goes up, and only a game the artist authorises can raise it. Press the
> button on its chest and it waves. It plays in any glTF viewer, and comes alive in an HVYM player.

**Status:** early. The format is a draft (version 0.1), with a validator and an example. The
Blender add-on, the player and the contracts are planned. See [docs/PLAN.md](docs/PLAN.md).

## Read

- [docs/VISION.md](docs/VISION.md): what this is for, and the principles.
- [spec/HVYM_asset.md](spec/HVYM_asset.md): the format (`HVYM_asset` and `HVYM_node_control`, glTF
  extensions).
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): authoring, hosting, ownership, the player, games.
- [docs/OWNERSHIP.md](docs/OWNERSHIP.md): copies, sales and enforced rules on Stellar.
- [docs/ORIGINAL.md](docs/ORIGINAL.md): the first Heavymeta Standard (2022–2025), and what carried
  over.

## Try it

The example, Lantern Bot, is in [examples/lantern-bot/](examples/lantern-bot/).

To validate an asset:

```sh
pip install -r requirements-dev.txt
python tools/validate.py examples/lantern-bot/lantern-bot.glb
python -m unittest discover -s tests
```

To play it in Babylon.js, headlessly, and check that the chest button waves the arm (Node 22):

```sh
cd tools/babylon && npm install && npm run check
```

To rebuild the example and render it with a state applied (Blender 4.2 or later):

```sh
blender -b --factory-startup --python tools/blender/make_example.py -- examples/lantern-bot
blender -b --factory-startup --python tools/blender/preview.py -- examples/lantern-bot/lantern-bot.gltf out.png '{"hat": 1, "paint": 1, "mood": 1}'
```

## Layout

| Path | What |
|---|---|
| `spec/` | The format spec and its JSON Schemas. |
| `tools/validate.py` | The validator. |
| `tools/blender/` | Builds the example, and renders an asset with a state. |
| `examples/` | Example assets. |
| `tests/` | Validator tests. |
| `docs/` | Vision, architecture, ownership design, plan, and the original system. |

## Licences

- **Spec text** (`spec/*.md`, `docs/`): [CC BY 4.0](LICENSE-SPEC), like Khronos specs.
- **Schemas, tools, examples and the coming player:** [MIT](LICENSE).
- **The coming Blender add-on:** GPL-3.0-or-later, as Blender requires of code that imports `bpy`.

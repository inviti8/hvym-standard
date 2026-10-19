# Lantern Bot

A small robot that shows each part of the format. It's built by `tools/blender/make_example.py`;
don't edit the files by hand.

| File | What |
|---|---|
| `lantern-bot.gltf` + `lantern-bot.bin` | Readable JSON, for studying the format. |
| `lantern-bot.glb` | The same asset as one file. |

## What's in it

| Property | Type | Lifetime | Drives |
|---|---|---|---|
| `name` | string, ≤ 24 bytes | mint | (shown in the panel) |
| `hat` | choice: Cone, Top hat | mint | the `hat` set of nodes |
| `paint` | choice: Red, Blue | mint | the `paint` set of materials on the body |
| `mood` | float 0–1 | view | the mouth's Smile morph target |
| `lamp` | colour | view | the lantern's emissive colour |
| `lamp_on` | bool | view | the lantern's visibility. The cube on its chest is a toggle control for it. |
| `dance` | bool | view | the Dance animation, looping |
| `xp` | int 0–1,000,000 | live, increase, by delegate | (a stat) |
| `durability` | int 0–100 | live, decrease by 1, by delegate | (a stat) |
| `series` | int | constant | (a stat) |

Behaviour is a KHR_interactivity graph:
- Pressing the round chest button plays Wave. That's core `event/onSelect`, so it works in any
  KHR_interactivity viewer.
- A change to `xp` also plays Wave, through `hvym/property/onChange`. That event also fires once
  when the copy's values load, so the bot waves hello. It needs an HVYM player.

## Try it

- **Any glTF viewer** (Blender, model-viewer, three.js editor) shows it with the cone hat, red paint
  and a flat mouth: its defaults. A viewer without `KHR_node_visibility` also shows the hidden top
  hat.
- **The Babylon.js sandbox** (sandbox.babylonjs.com) supports KHR_interactivity. Drop
  `lantern-bot.glb` in and click the chest button: the right arm should wave. This is untested so
  far; see `docs/PLAN.md`, phase 1.
- **Render a state:**
  `blender -b --factory-startup --python tools/blender/preview.py -- examples/lantern-bot/lantern-bot.gltf out.png '{"hat": 1, "paint": 1, "mood": 1}'`

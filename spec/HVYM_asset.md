# HVYM_asset and HVYM_node_control

## Contributors

- Fibo Metavinci, HEAVYMETA

## Status

**Draft, version 0.1.** Breaking changes are expected before 1.0. The `HVYM` prefix is not yet
registered with Khronos ([PLAN.md](../docs/PLAN.md), phase 8).

## Dependencies

Written against the glTF 2.0 specification. It works with these extensions and uses them where they
are present:

- [KHR_interactivity](https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_interactivity),
  ratified 2026-08-30. This spec cites the registry at commit `8c8fb8a5` (2026-10-12).
- [KHR_node_visibility](https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_node_visibility)
- [KHR_node_selectability](https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_node_selectability)
- [KHR_node_hoverability](https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_node_hoverability)
- [KHR_materials_variants](https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_materials_variants)
- The [glTF Asset Object Model](https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/ObjectModel.adoc),
  for pointers.

The key words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.

## Overview

`HVYM_asset` turns a glTF asset into a **programmable asset**. The asset declares **properties**:
typed values, each with a rule for who may change it and how. **Bindings** connect properties to
the scene, so that a property drives a morph weight, a material colour, a node's visibility or an
animation. **Sets** are groups of alternatives (hats, paints) that a property chooses between.
**Panels** describe how a player presents properties to people. `HVYM_node_control`, on a node,
makes that node's mesh a control: a button, toggle, slider, selector or text field.

Behaviour, meaning what happens when someone clicks something, is not redefined here. It's a
KHR_interactivity graph. This spec adds three graph operations so that graphs can read, change and
react to properties.

An asset file is a **template**: it's immutable and identified by its content hash. Each owned
**copy** of it has its own **state**: the current values of its `mint` and `live` properties.
State lives outside the file, on a ledger for owned copies ([OWNERSHIP.md](../docs/OWNERSHIP.md)).
A player applies state over the template's defaults.

### Graceful fallback

A viewer that knows none of this still shows the asset correctly at its defaults. Exporters
**MUST** write the glTF so that its plain content is the default state:
- morph weights at the properties' defaults;
- the default option of each set visible or applied, and the others hidden through
  `KHR_node_visibility`;
- materials at their default factors.

`HVYM_asset` and `HVYM_node_control` **MUST** be listed in `extensionsUsed`. They **MUST NOT** be
listed in `extensionsRequired`.

## Concepts

| Term | Meaning |
|---|---|
| Template | The glTF file. Immutable once published. |
| Copy | One owned instance of a template, like edition 12 of 50. |
| Property | A named, typed value with a rule. |
| Lifetime | When a property's value can change: `view`, `constant`, `mint` or `live`. |
| Binding | How a property's value drives something in the scene. |
| Set | A list of alternatives (nodes or materials) that a property selects between. |
| Control | A node whose mesh acts as a UI control. |
| Panel | A group of properties shown together, optionally anchored to a node. |
| State | A copy's current values for its `mint` and `live` properties. |
| Host | The application running the player: a web page, a game, a wallet. |

## The root extension: `HVYM_asset`

```json
"extensions": {
  "HVYM_asset": {
    "specVersion": "0.1",
    "kind": "character",
    "title": "Lantern Bot",
    "creator": { "name": "Fibo Metavinci", "address": "stellar:GD6S...MKJG" },
    "properties": [ ... ],
    "sets": [ ... ],
    "bindings": [ ... ],
    "panels": [ ... ]
  }
}
```

| Field | Type | Required | Meaning |
|---|---|---|---|
| `specVersion` | string | yes | The version of this spec the asset follows, `"0.1"`. |
| `kind` | string | no | What the asset is: `character`, `creature`, `weapon`, `object`, `wearable`, `audio`, `scene` or `other`. Default `other`. |
| `title` | string | no | The asset's display name. |
| `creator` | object | no | `name` (string) and `address` (string, a ledger address in `<network>:<address>` form, like `stellar:G...`). This is informational. Proof of authorship comes from the collection contract and, later, a C2PA manifest. |
| `tags` | string[] | no | Free keywords. |
| `properties` | object[] | yes | At least one [property](#properties). |
| `sets` | object[] | no | [Sets](#sets). |
| `bindings` | object[] | no | [Bindings](#bindings). |
| `panels` | object[] | no | [Panels](#panels). |

Every object in this spec may carry `extensions` and `extras`, as glTF objects do.

## Properties

```json
{ "name": "xp", "label": "Experience", "type": "int",
  "default": 0, "min": 0, "max": 1000000,
  "lifetime": "live", "change": "increase", "by": ["delegate"] }
```

| Field | Type | Required | Meaning |
|---|---|---|---|
| `name` | string | yes | An identifier, unique in the asset, matching `^[a-z][a-z0-9_]{0,31}$`. Games, state documents and contracts use it. The limit of 32 characters fits a Soroban `Symbol`. |
| `label` | string | no | A display name. Defaults to `name`. |
| `description` | string | no | A sentence for people. |
| `type` | string | yes | `bool`, `int`, `float`, `color`, `choice` or `string`. |
| `default` | value | yes | The value in the template. See [values](#values). |
| `min`, `max` | number | `int`, `float` | The inclusive range. `min` ≤ `default` ≤ `max`. |
| `options` | string[] | `choice` | The choices' labels, at least two. Values are indices into this list. |
| `maxLength` | integer | `string` | The maximum length in UTF-8 bytes, 1 to 256. Default 64. |
| `decimals` | integer | no | For `float` with lifetime `mint` or `live`: the decimal places kept in state, 0 to 9, default 3. Values are rounded to this precision when stored. |
| `lifetime` | string | yes | `view`, `constant`, `mint` or `live`. See below. |
| `change` | string | `live` | How a `live` value may change: `set`, `increase`, `decrease` or `step`. |
| `amount` | number | no | For `increase`, `decrease` and `step`: the exact size of each change. If it's absent, any size is allowed. |
| `by` | string[] | `live` | Who may change a `live` value: any of `owner`, `creator` and `delegate`. At least one. |

### Lifetimes

| Lifetime | Who sets it | Stored | Meaning |
|---|---|---|---|
| `view` | Anyone viewing | No | A viewer's own adjustment: spin the turntable, open the visor, try the other hat. It is reset on reload. Players MAY remember it locally. |
| `constant` | The creator, in the file | No | The same for every copy and never changes: a series number, a birth date. |
| `mint` | The buyer, at purchase | Yes | Chosen once, within the property's range or options, then fixed for that copy: its name, its paint. If the buyer doesn't choose, it's `default`. |
| `live` | Whoever `by` names, under the `change` rule | Yes | Changes over the copy's life: experience, durability, charge. |

### Change rules, for `live` properties

| Change | Allowed | Valid types |
|---|---|---|
| `set` | Any value in range (any option, for `choice`; any string up to `maxLength`) | all |
| `increase` | New value > old value. If `amount` is present, new = old + `amount`. | `int`, `float` |
| `decrease` | New value < old value. If `amount` is present, new = old − `amount`. | `int`, `float` |
| `step` | Either direction. If `amount` is present, by exactly `amount`. | `int`, `float` |

Values never leave `[min, max]`. A change that would cross a bound is refused, not clamped, so a
rule can't be bent by asking for more than the range holds. A `bool` with `change: set` toggles
freely. `increase` on a `bool` is a one-way latch from false to true, written as
`"type": "int", "min": 0, "max": 1, "change": "increase"`.

### Authority

| `by` | Who |
|---|---|
| `owner` | The copy's current owner. |
| `creator` | The collection's creator. |
| `delegate` | An address the creator has authorised in the collection contract, typically a game. Delegates are bound by the same rule as everyone else. |

The file declares the rule. For owned copies the contract enforces it
([OWNERSHIP.md](../docs/OWNERSHIP.md)). A player MUST NOT apply a change to a stored property
until the ledger has accepted it.

### Values

| Type | JSON value | In graphs |
|---|---|---|
| `bool` | `true` / `false` | float 1 / 0 |
| `int` | integer, within ±(2^53 − 1) | float. Exact up to ±2^24. |
| `float` | number | float |
| `color` | four numbers 0–1, `[r, g, b, a]`, linear, like glTF colour factors | not available |
| `choice` | integer index into `options` | float (the index) |
| `string` | string | not available |

## Sets

A set is a list of alternatives. Exactly one option is active at a time. A `choice` or `int`
property selects it through a [binding](#bindings). The **default option** is that property's
`default`, or option 0 when no binding drives the set.

```json
{ "name": "hat", "type": "nodes", "options": [4, 5] }
{ "name": "paint", "type": "materials", "options": [1, 2],
  "targets": [ { "mesh": 0, "primitive": 0 } ] }
```

| Field | Type | Required | Meaning |
|---|---|---|---|
| `name` | string | yes | An identifier, unique among sets. |
| `type` | string | yes | `nodes` or `materials`. |
| `options` | integer[] | yes | At least two node indices (`nodes`) or material indices (`materials`). |
| `targets` | object[] | `materials` | The primitives that wear the chosen material: `{ "mesh": i, "primitive": j }`. |

- **A `nodes` set:**
  - The active option's node is visible and the others are hidden, subtree and all, with the
    meaning of `KHR_node_visibility`.
  - Each option node MUST carry `KHR_node_visibility`, `true` for the default option and `false`
    for the others.
- **A `materials` set:**
  - It assigns the active option's material to every target primitive.
  - Each target primitive's `material` in the file MUST be the default option.
- **Fallback for a single material set:** when an asset has exactly one `materials` set, exporters
  SHOULD also write it as `KHR_materials_variants`, so commerce viewers can switch it.
  KHR_interactivity can't change a primitive's material, and the variants extension makes one
  global choice. That's why the set is defined here and the variants extension is only a fallback.

## Bindings

A binding connects a property to one target. A property may have several bindings: `mood` can
drive a brow morph and the cheeks' colour at once.

```json
{ "property": "mood", "pointer": "/nodes/2/weights/0" }
{ "property": "door", "pointer": "/nodes/7/translation",
  "map": { "from": [0, 1], "to": [[0, 0, 0], [0.4, 0, 0]] } }
{ "property": "hat", "set": "hat" }
{ "property": "dance", "animation": 1, "drive": "play", "loop": "repeat" }
```

| Field | Type | Meaning |
|---|---|---|
| `property` | string | The property's `name`. |
| `pointer` | string | Target kind 1: a glTF Object Model pointer to a mutable property. |
| `set` | string | Target kind 2: a set's `name`. |
| `animation` | integer | Target kind 3: an animation index. |
| `drive` | string | For `animation`: `play`, `weight` or `time`. |
| `loop` | string | For `animation`: `once`, `repeat`, `pingpong` or `hold`. Default `once`. |
| `map` | object | Optional linear mapping, `{ "from": [a, b], "to": [c, d] }`. |

A binding has exactly one of `pointer`, `set` and `animation`.

### Pointers

Pointers use the glTF Object Model syntax with concrete indices. Version 0.1 allows these targets:

| Pointer | Target type |
|---|---|
| `/nodes/{n}/translation`, `/nodes/{n}/scale` | float3 |
| `/nodes/{n}/rotation` | float4 (a quaternion) |
| `/nodes/{n}/weights/{w}`, `/meshes/{m}/weights/{w}` | float |
| `/nodes/{n}/extensions/KHR_node_visibility/visible` | bool |
| `/materials/{m}/pbrMetallicRoughness/baseColorFactor` | float4 |
| `/materials/{m}/pbrMetallicRoughness/metallicFactor`, `.../roughnessFactor` | float |
| `/materials/{m}/emissiveFactor` | float3 |
| `/materials/{m}/extensions/KHR_materials_emissive_strength/emissiveStrength` | float |
| `/materials/{m}/alphaCutoff` | float |

Which property types can drive which targets:

| Property type | Pointer target | With `map` |
|---|---|---|
| `float`, `int` | float | `to` is two numbers. Default: the value is used as it is. |
| `float`, `int` | float3 / float4 | Required. `to` is two vectors, and the value interpolates between them (rotations SHOULD use slerp). |
| `bool` | bool | none |
| `bool` | float | `to` gives the false and true values. Default `[0, 1]`. |
| `color` | float4 | none: the colour is used as it is |
| `color` | float3 | none: alpha is dropped |

`map.from` defaults to `[min, max]`. Mapping is linear and clamped to `from`.

### Sets

`set` names a set. The property MUST be a `choice` with as many options as the set, or an `int`
whose range lies within the set's indices. The value is the active option.

### Animations

| `drive` | Property type | Meaning |
|---|---|---|
| `play` | `bool` | True starts the animation, from the beginning; false stops it. `loop` applies. |
| `weight` | `float` | The animation's blend weight, `map`ped to 0–1. The animation plays, looping, while the weight is above 0. |
| `time` | `float` | The playhead, `map`ped to 0–1 of the animation's length. It scrubs a paused animation. |

An animation driven by a binding SHOULD NOT also be started or stopped by a graph. The result of
doing both is up to the player.

## Panels

Panels say how a player presents properties. They're hints: a player MAY show properties in its
own UI, and MUST NOT offer changes the rules don't allow. Properties in no panel are not shown.

```json
{ "name": "Lantern Bot", "anchor": 9, "align": "left",
  "colors": { "primary": [0.04, 0.48, 0.34, 1], "text": [1, 1, 1, 1] },
  "groups": [ { "label": "Look", "properties": ["hat", "paint", "mood"] },
              { "label": "Stats", "properties": ["xp", "battery"] } ] }
```

| Field | Type | Meaning |
|---|---|---|
| `name` | string | The panel's title. |
| `anchor` | integer | Optional node index. The panel sits at this node in the scene. Without one, it's an overlay. |
| `align` | string | `center`, `left` or `right`, relative to the anchor. Default `center`. |
| `colors` | object | Optional `primary`, `secondary` and `text`, each a linear `[r, g, b, a]`. |
| `groups` | object[] | `{ "label", "properties": [names] }`, in display order. |

For each property, a player picks a widget from its type and rule:
- a slider or meter for numbers;
- a toggle for `bool`;
- a selector for `choice`;
- a text field for `string`.

A `constant` property is shown read-only. A stored property is editable only by someone allowed to
change it.

## Controls: `HVYM_node_control`

On a node. The node's mesh becomes a control in the scene.

```json
"nodes": [ { "name": "ChestButton", "mesh": 3,
             "extensions": { "HVYM_node_control": { "type": "button", "event": "wave" } } } ]
```

| Field | Type | Meaning |
|---|---|---|
| `type` | string | `button`, `toggle`, `slider`, `selector` or `text`. |
| `property` | string | The property it changes or shows. Required for every type except `button`. |
| `event` | string | For `button`: the id of a custom event sent when it's pressed. |
| `handle` | integer | For `slider`: the node that moves. Default: the control's first child. |
| `axis` | string | For `slider`: `x`, `y` or `z` in the control node's space. Default `x`. |
| `length` | number | For `slider`: the handle's travel in metres, from `min` at 0 to `max` at `length`. Default 1. |
| `wrap` | boolean | For `selector`: whether stepping past the last option returns to the first. Default true. |

| Type | Property type | On select |
|---|---|---|
| `button` | none | Sends the custom event `event`, to graphs (`event/receive` with that `id`) and to the host. |
| `toggle` | `bool` | Flips the value. |
| `slider` | `int`, `float` | Dragging the handle sets the value. |
| `selector` | `choice`, `int` | Steps to the next option. |
| `text` | `string` | Shows the value on the node's mesh, and edits it when allowed. |

- A control changes its property only as the property's rules allow. A `view` property changes at
  once. A stored property's change goes to the host, which submits it to the ledger.
- Controls are selectable nodes. If a control node carries `KHR_node_selectability` with
  `selectable: false`, the control is disabled.
- Players SHOULD show hover feedback on control nodes, and honour `KHR_node_hoverability`.

## Behaviour: KHR_interactivity operations

Behaviour is a KHR_interactivity graph. This spec defines three operations. Their declarations name
`"extension": "HVYM_asset"`. A viewer that doesn't support them treats them as no-ops, as
KHR_interactivity requires.

All three take a `configuration` value `property`: an `int`, the property's index in `properties`.
Graphs have no string type, so properties are referenced by index here.

| Operation | Sockets | Meaning |
|---|---|---|
| `hvym/property/get` | out value `value: float` | The property's current value, as in [values](#values). Not available for `color` and `string`. |
| `hvym/property/set` | in flow `in`; in value `value: float`; out flows `out`, `err` | Requests a change. `out` fires if the rules and the viewer's authority allow it: a `view` value changes at once, and a stored value is handed to the host. `err` fires otherwise. The new value of a stored property arrives later, through `onChange`. |
| `hvym/property/onChange` | out flow `out`; out value `value: float` | An event. Fires once when the copy's values are known, then after every change. |

```json
"types": [ { "signature": "float" }, { "signature": "int" } ],
"declarations": [
  { "op": "hvym/property/onChange", "extension": "HVYM_asset",
    "outputValueSockets": { "value": { "type": 0 } } },
  { "op": "animation/start" }
],
"nodes": [
  { "declaration": 0, "configuration": { "property": { "value": [3] } },
    "flows": { "out": { "node": 1 } } },
  { "declaration": 1, "values": {
      "animation": { "type": 1, "value": [0] },
      "startTime": { "type": 0, "value": [0] },
      "endTime": { "type": 0, "value": [1] },
      "speed": { "type": 0, "value": [1] } } }
]
```

**Host calls** use KHR_interactivity's custom events. A graph's `event/send` with an `id` reaches
the host, and the host answers through `event/receive`. The meaning of each id is between the asset
and its host. This replaces the old system's calls to backend methods by name.

## State

A copy's state is the values of its `mint` and `live` properties, keyed by name:

```json
{ "asset": "bafybeigdyrzt5...", "copy": 12,
  "values": { "name": "Ember", "hat": 1, "paint": 0, "xp": 340, "battery": 72 } }
```

- `asset` is the template's IPFS CID, and `copy` is the copy's number.
- Properties missing from `values` take their defaults.
- A player applies state over the defaults, then applies bindings.
- The ledger holds the authoritative state of an owned copy. This document is how hosts exchange it.

## Validation

An asset is invalid if any of these fail. `tools/validate.py` checks them.

1. Each extension object matches its JSON Schema in [schema/](schema/).
2. `HVYM_asset` is in `extensionsUsed`. If a node carries `HVYM_node_control`, that is in
   `extensionsUsed` too. Neither is in `extensionsRequired`.
3. Property names are unique, and set names are unique.
4. Each property's fields suit its type and lifetime:
   - `min` ≤ `default` ≤ `max`;
   - `choice` has at least two options, and its default is a valid index;
   - `string` defaults fit `maxLength`;
   - `change` and `by` are present exactly when the lifetime is `live`;
   - `increase`, `decrease` and `step` apply only to `int` and `float`;
   - `amount` is positive.
5. Every index points at something that exists: set options, targets, binding animations,
   pointer indices, panel anchors, control handles and graph `property` configurations.
6. Every binding names an existing property, has exactly one target, and its property type suits
   that target (the tables above). Pointers are on the allowed list, and their indices exist,
   including the morph target index.
7. A `nodes` set's option nodes carry `KHR_node_visibility`, `true` only on the default option. A
   `materials` set's targets use the default option in the file. At most one binding drives each
   set.
8. A control's property exists and suits its type. A `button` has an `event`.
9. Panel groups name existing properties.
10. The plain file shows the defaults: each pointer binding's target holds, in the file, the value
    the binding gives for its property's default (with glTF's own defaults where the file omits
    the value).

## Known implementations

- `tools/validate.py` in this repo validates assets. It isn't a player.
- The Blender add-on, the player and the contract are planned ([PLAN.md](../docs/PLAN.md)).

## Resources

- [docs/VISION.md](../docs/VISION.md): why the format exists.
- [docs/ORIGINAL.md](../docs/ORIGINAL.md): the first Heavymeta Standard, and how its parts map to these.
- [docs/OWNERSHIP.md](../docs/OWNERSHIP.md): how owned copies and their state work on Stellar.
- [examples/lantern-bot/](../examples/lantern-bot/): a complete example asset.

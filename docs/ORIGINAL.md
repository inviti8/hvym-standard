# The original system (2022–2025)

The first Heavymeta Standard was built on the Internet Computer (ICP). This is the record of what
it was, what it got right, and what broke. The new design carries over the ideas and none of the
code. Sources: a full read of the add-on, the CLI and the runtime in October 2026.

## The pieces

| Piece | Repo | What it did |
|---|---|---|
| Blender add-on | [heavymeta_standard](https://github.com/inviti8/heavymeta_standard) (MIT, ~4,900 lines in one file) | Authoring. Panels on collections, objects and the NLA editor; a glTF export hook writing the `HVYM_nft_data` extension. |
| `hvym` CLI | [heavymeta-cli-dev](https://github.com/inviti8/heavymeta-cli-dev) (Python, Click) | Built the extension's JSON from the add-on's data. Managed ICP identities, scaffolded projects from template repos, rendered Motoko canisters and web pages from Jinja templates, deployed with `dfx`. The ICP commands were removed in October 2025. |
| `hvym-proprium` runtime | in the CLI repo, `npm_links/proprium` (three.js 0.158, ~12,700 lines in one file) | Loaded the glTF, built an in-scene 3D widget kit (text, panels, sliders, toggles, selectors) from the extension, and called canister methods. |
| Templates | `hvym_model_debug_template`, `hvym_minter_template`, `hvym_custom_client_template`, `hvym_assets_template` | A local model preview, a minter with Internet Identity and Plug, a client with your own Motoko backend, and plain asset hosting. |

## The authoring flow

1. Choose a project type (model preview, minter, custom client) and an ICP identity.
2. On each Blender collection, add **traits**:
   - value properties;
   - text properties;
   - calls;
   - mesh toggles;
   - mesh sets, morph sets, material properties and material sets;
   - animations.
3. In the NLA editor, define **actions**: sequences of animation tracks, played on click, double
   click, mouse wheel or a named event, on the whole model or on one mesh.
4. On mesh objects, mark **interactables**: a mesh that acts as a button, toggle, slider, selector
   or text field, wired to a backend method by name.
5. Add a **menu transform**, an empty that anchors the collection's in-scene menu, with colours
   and alignment.
6. Export, then debug locally or deploy to a canister.

## The data model, briefly

Everything went into one root-level glTF extension, `HVYM_nft_data`:

```text
project:       { name, type }
contract:      { mintable, nftType, nftChain, nftPrice, premNftPrice, maxSupply, minterType,
                 minterName, minterDesc, minterImage, minterVersion, enableContextMenus,
                 menuIndicatorsShown }
interactables: { <object name>: { interaction_type, call, param_type, ... } }
<collection id>: {
  collectionName, collectionType,
  valProps, textValProps, callProps, meshProps, meshSets, morphSets, animProps, matProps,
  materialSets, menuData, propLabelData, nodes, actionProps
}
```

**Value properties** had a default, a min and a max, a widget, an `immutable` flag ("minted, and
can't be updated after minting"), and an **action type**:

| Action type | Meaning |
|---|---|
| `Static` | Display only. |
| `Incremental` | Raised by a fixed amount. |
| `Decremental` | Lowered by a fixed amount. |
| `Bicremental` | Raised or lowered. |
| `Setter` | Set to any value in range. |
| `Getter` | Read from the backend. |

The NFT type codes were Character, Immortal, Animal, Weapon, Object, Generic and Auricle (HVYC, HVYI,
HVYA, HVYW, HVYO, HVYG, HVYAU).

## What it got right

These ideas carry into the new design:

- **One extension over an ordinary glTF.** A plain viewer ignores it and still shows the model.
- **Properties with rules.** The action types are game-stat semantics, and the `immutable` flag is
  the idea of a value chosen at purchase and fixed after. These are the core of the new format.
- **The appearance vocabulary**:
  - mesh toggles;
  - exclusive mesh sets (swap the hat);
  - material sets applied to a mesh set (choose the paint);
  - morph sets (sliders over shape keys);
  - exposed material fields;
  - animations as toggles or weights.
- **Actions.** Sequences of clips triggered by a gesture or an event: simple behaviour an artist can
  author without code.
- **Authored meshes as controls.** A mesh in the scene becomes a button, slider or selector, with
  its child mesh as the handle. This was the most distinctive feature.
- **In-scene menus.** Each collection had a menu anchored to a point in the scene, with its own
  colours and labels.
- **State as a patch over the authored defaults.** The runtime kept an edited copy of the data and
  could rebuild the model from a saved copy. That's the right model for per-copy state.
- **One call seam.** The runtime reached the backend through `call(method, arg)` with a guard.

## What broke, and why

### The format was never written down

- The add-on stopped defining the JSON in April 2024. It sent its Blender data to the CLI by
  reflection, and the CLI's data classes became the de facto format.
- The format had no schema and no version field.
- Several CLI constructors were broken.
- The add-on, the CLI and the runtime disagreed on key names and values. For example:
  - `LoopRepeat` was written, but the runtime expected `LoopForever`.
  - The runtime read `blend` where `blending` was written.
  - Behaviours had two different shapes.
  - The Motoko template read `nftName`, which didn't exist.
- There was a mix of casing styles and typos baked into identifiers (`onlyOnwner`, `irridescent`).

### References were by name

- Nodes, materials and animations were found by name.
- Collections were keyed by a weak 8-character random id.
- The menu anchor was found by the naming convention `menu_<id>`.
- Blender renames things on export, and glTF names needn't be unique, so lookups broke silently.

### Properties drove nothing

- A value property's action type only decided which canister buttons appeared (`increment_<name>`).
- Nothing linked a property to a morph, a material, a node or an animation, so "stats" were numbers
  in a panel.
- Controls were wired to backend methods by name only, never to properties.

### The chain side never worked end to end

- The canister template:
  - hard-coded a property called `Ammo`;
  - didn't compile for `set_`;
  - stored only natural numbers;
  - let anyone mint;
  - kept uploaded images in non-stable memory;
  - never enforced the price or the supply.
- The runtime called `increment_<name>` without the token id the canister required.
- The design also stored the whole edited JSON as the token's metadata, so a token's state was
  unvalidated JSON that any client could write.

### The runtime was fragile

- It was a 12,700-line single module with a global scene singleton.
- Input was mouse-only, it relied on DOM-id globals, and it kept one global `localStorage` key.
- A missing or hidden item silently dropped the rest of its group: a `return` where `continue` was
  meant, in about seven loops.
- Shared animation mixers ran clips at several times their speed.
- Morph sets worked only on grouped meshes.

### The tooling depended on a separate executable

- The add-on couldn't export without the CLI installed, and it called the CLI at import time.
- The CLI's template downloads pointed at a branch that didn't exist.

### The platform

The author moved away from ICP. The new design is chain-neutral in the format, and uses Stellar for
ownership.

## From old to new

| Old | New (see [spec/HVYM_asset.md](../spec/HVYM_asset.md)) |
|---|---|
| `HVYM_nft_data`, one root object keyed by collection id | `HVYM_asset` at the root, plus `HVYM_node_control` on nodes. Arrays and glTF indices, with a `specVersion`. |
| Value property + action type + `immutable` | A **property** with a `type` and a `lifetime` (`view`, `constant`, `mint`, `live`). A `live` property has a `change` rule (`set`, `increase`, `decrease`, `step`) and an authority `by` (`owner`, `creator`, `delegate`). |
| `Static` | `lifetime: constant` |
| `immutable: true` | `lifetime: mint` (chosen at purchase, then fixed) |
| `Incremental` / `Decremental` / `Bicremental` / `Setter` | `live` with `change: increase` / `decrease` / `step` / `set` |
| `Getter` | Not needed. Every `live` value is read from the copy's state. |
| Text property | A property of `type: string` |
| Call property, and calls by method name | Custom events in a KHR_interactivity graph (`event/send` and `event/receive`), which the host answers |
| Mesh prop (visibility toggle) | A `bool` property bound to `KHR_node_visibility` |
| Mesh set | A `nodes` **set**, selected by a `choice` property |
| Material set | A `materials` **set** with explicit target primitives |
| Morph set | `float` properties bound to `/nodes/N/weights/M`, grouped in a panel |
| Material property (exposed fields) | Properties bound to material pointers (`baseColorFactor`, `roughnessFactor`...) |
| Anim prop (toggle or weight) | A binding to an animation: `play`, `weight` or `time` |
| Action (clip sequence on a gesture) | A KHR_interactivity graph. The add-on compiles simple actions into graphs. |
| Interactable mesh | `HVYM_node_control` on the node: `button`, `toggle`, `slider`, `selector` or `text`, bound to a property or an event |
| Menu + menu transform + labels | A **panel** with an `anchor` node, colours and labelled groups |
| `contract` (price, supply, minter type) | Not in the file. It's the collection contract's configuration ([OWNERSHIP.md](OWNERSHIP.md)). |
| NFT type codes | `kind`: `character`, `creature`, `weapon`, `object`, `wearable`, `audio`, `scene`, `other` |

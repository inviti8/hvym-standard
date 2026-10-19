# Architecture

How the pieces fit together, from an artist's Blender file to a copy someone owns and plays.
The format itself is [spec/HVYM_asset.md](../spec/HVYM_asset.md), and the ledger side is
[OWNERSHIP.md](OWNERSHIP.md).

## The layers

```text
   Blender add-on (+ Polyface)            authoring: properties, rules, bindings, controls, behaviour
            │ exports
            ▼
   glTF + HVYM_asset + KHR_interactivity  the template: one open file, valid at its defaults
            │ validate, publish
            ▼
   IPFS (Pintheon)                        the template's content hash (CID) is its identity
            │ creator deploys
            ▼
   Collection contract (Soroban)          editions, sales, owners, per-copy state, rules enforced
            │ read state / submit changes
            ▼
   Player  <hvym-model>   ·   games (importers)   ·   wallets and markets (SEP-50)
```

Each layer works without the ones below it:
- A template plays at its defaults in any glTF viewer.
- In an HVYM player, its `view` properties, controls and behaviour all work, with no ledger at all.
- Ownership adds the stored properties: `mint` and `live`.

## The pieces

### 1. The format

- **What:** glTF 2.0 with `HVYM_asset` at the root, `HVYM_node_control` on nodes, and behaviour as
  a KHR_interactivity graph.
- **Owns:** properties and their rules, bindings, sets, panels, controls, and the three graph
  operations.
- **Doesn't own:** price, supply, owners, current values. Those belong to the contract.
- **Lives in:** `spec/`. The prose spec, JSON Schemas, and `tools/validate.py`.

### 2. Authoring: the Blender add-on

- A Blender 4.2+ extension, like Polyface, written fresh. It's GPL-3.0-or-later because it
  imports `bpy`.
- It writes the format directly in the glTF exporter's hooks. No CLI, no round trips.
- **Panels:**
  - **Properties:** add a property, pick its type and lifetime, and for `live`, its change rule and
    who may change it.
  - **Bindings:** pick what a property drives from the scene itself. A shape key, a material input,
    an object's visibility, an action. The add-on turns the pick into a pointer with indices at
    export.
  - **Sets:** select objects or materials and make a set. The add-on keeps unused set materials in
    the export (the exporter drops materials no face uses).
  - **Controls:** mark an object as a button, toggle, slider, selector or text field.
  - **Actions:** simple behaviour recipes, such as "when this is pressed, play these animations in
    order". The add-on compiles them into a KHR_interactivity graph. Blender can't author graphs,
    and artists shouldn't have to.
  - **Panels:** group properties and pick an anchor object.
- **Export:** it applies the defaults to the scene before export, so the file shows the defaults
  (validation rule 10). It writes `KHR_node_visibility` for sets, and validates before writing.
  Errors name the Blender object or property at fault.
- **Preview:** it applies a state in the viewport, so the artist can see "Blue paint, top hat,
  smiling" without leaving Blender.
- **Lives in:** `addon/` (phase 2).

### 3. Polyface: talking characters

[Polyface](https://github.com/inviti8/polyface) gives a face a rig, a voice and lip sync. An HVYM
character built with it gets:
- **Expression bindings.** Properties like `mood` bound to the face's ARKit-named morph targets.
- **Lines.** Each spoken line is an animation (the lip sync, baked to morph weights) plus an audio
  clip. A graph or a button plays a line.
- **Audio.** glTF has no ratified audio yet: KHR_audio_emitter is still a draft and KHR_audio_graph
  is a proposal. So version 0.2 of the spec adds a small HVYM audio reference that can map onto
  whichever Khronos lands.

### 4. Hosting: IPFS through Pintheon

- The template GLB is pinned to IPFS. Its CID names it everywhere: in the contract, in state
  documents, in token metadata.
- A preview image and the SEP-50 token metadata JSON are pinned beside it.
- Pintheon nodes and the pin-service contract keep it available. Anyone else can pin it too, which
  is the point of content addressing.

### 5. Ownership: the collection contract

- **One Soroban contract per collection.** A collection is one template and its editions. The
  contract is deployed by the creator's key through a factory.
- **What it does:**
  - Implements the SEP-50 NFT interface, so wallets and markets see copies.
  - Sells editions for USDC, paying the creator directly.
  - Stores each copy's `mint` and `live` values.
  - Enforces each property's rule, and charges royalties on its own resale path.
- **Details:** [OWNERSHIP.md](OWNERSHIP.md).

### 6. The indexer

- RPC nodes keep contract events for about a week. A small indexer follows the contracts' events
  and keeps a fast, permanent view: copies, owners, values, history.
- The player reads it for speed and falls back to the contract for truth.

### 7. The player: `<hvym-model>`

A web component anyone can put on a page:

```html
<script type="module" src="https://cdn.jsdelivr.net/npm/hvym-player/dist/hvym-model.js"></script>
<hvym-model src="ipfs://bafy.../lantern-bot.glb" copy="stellar:CA...:12"></hvym-model>
```

- **Loads** the template, and validates it.
- **Applies** the copy's state, if a `copy` attribute is set, over the defaults, then the
  bindings.
- **Runs:**
  - controls with pointer events (mouse, touch, and later XR);
  - panels as an accessible overlay, or anchored in the scene;
  - KHR_interactivity graphs, including the HVYM operations.
- **Changes** stored properties through the host's wallet connection. It never holds keys.
- **Each instance has its own state.** There are no globals, and many models can share one page.
- **Engine: Babylon.js.** It has the most complete KHR_interactivity support (ratified Phase 1,
  merged September 2026), plus KHR_materials_variants, node visibility, selectability and
  hoverability. Graphs work without us writing a graph interpreter. three.js has no official
  KHR_interactivity support. That's why the original runtime's three.js base doesn't carry over.
  This is a decision to confirm ([PLAN.md](PLAN.md)).

### 8. Games

- glTF is already every engine's interchange format. The game-side work is reading HVYM:
  properties as typed data on the imported asset, bindings applied, and controls exposed.
- **Godot first:** it's open source, and its glTF module supports document extensions
  (`GLTFDocumentExtension`), KHR_node_visibility and KHR_animation_pointer.
- **Unity next,** through UnityGLTF, which already runs KHR_interactivity.
- A game that wants to change `live` properties becomes a **delegate** of the collection. The
  creator authorises its address, and it's bound by the same rules as everyone.

### 9. Commerce

- **Primary sales:** the contract sells editions for USDC, paying the creator in the same
  transaction. A buyer with no USDC gets it through the Stripe on-ramp into their own wallet
  first. That's the same rail as HEAVYMETA's entitlements design
  (`heavymeta_collective/docs/ENTITLEMENTS.md`). HEAVYMETA never holds the money.
- **Resale:** through the contract's own listing and purchase, which pays the royalty. Plain
  SEP-50 `transfer` stays available for gifts.
- **Purchase choices:** `mint` properties are chosen in the purchase call. A creator can price
  some choices higher.

### 10. Provenance

- **Today:** the collection contract was deployed by the creator's key and records the template's
  CID. That's the proof of authorship.
- **Next:** a C2PA manifest embedded in the GLB, signed with an app CA from
  `hvym-cert-registry`. C2PA's GLB binding is in its working draft, with an experimental c2pa-rs
  feature proposed in October 2026. The manifest covers the immutable template, never per-copy
  state.

## How a copy's life goes

1. **Make.** The artist builds the character in Blender, adds properties and rules, previews
   states, and exports. The add-on validates.
2. **Publish.** The add-on, or the portal, pins the GLB and its preview to IPFS and gets the CID.
3. **Create the collection.** The artist's wallet calls the factory with:
   - the CID;
   - the rule table, derived from the file's `mint` and `live` properties;
   - supply, price and royalty.

   The factory deploys the collection contract, owned by the artist.
4. **Buy.** A buyer picks the purchase choices (hat, paint, name) and calls `buy`. USDC goes to
   the artist, and copy 12 is minted with its values.
5. **Play.** `<hvym-model src=… copy=…>` shows copy 12 as it is now.
6. **Change.**
   - The owner can't rename the copy, because `name` was fixed at purchase. They can top up
     `charge`, if its rule allows the owner.
   - A game that's a delegate raises `xp` by 50. The contract checks "increase, by delegate,
     within range" and records it.
   - The player sees the change event and the character updates.
7. **Resell.** The owner lists it. A buyer pays, the royalty goes to the artist, and the copy and
   its values move to the buyer.

## What's not decided yet

These are in [PLAN.md](PLAN.md)'s open decisions:
- the player engine;
- whether plain transfers are allowed in every collection;
- how delegates are added and removed;
- the co-op's share of sales, if any;
- whether to use one contract per collection or one shared contract.

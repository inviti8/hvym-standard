# Plan

The order of work, what's built, and the decisions made and still open. Keep this current: mark
phases built, add "As built" notes with anything measured, and record decisions as they're made.

## Phases

Each phase is useful on its own.

### Phase 0: foundations (built, 2026-10-18)

- The repo, [VISION.md](VISION.md), [ORIGINAL.md](ORIGINAL.md), [ARCHITECTURE.md](ARCHITECTURE.md),
  [OWNERSHIP.md](OWNERSHIP.md) and this plan.

### Phase 1: the format, version 0.1 (started, 2026-10-18)

- **Done:**
  - The spec, [spec/HVYM_asset.md](../spec/HVYM_asset.md).
  - JSON Schemas in `spec/schema/`.
  - `tools/validate.py`, which checks the schemas plus the ten validation rules.
  - Its tests, `tests/test_validate.py`.
  - The example asset `examples/lantern-bot/`, built by `tools/blender/make_example.py`.
  - `tools/blender/preview.py`, which renders an asset with a state applied.
- **Still to do:**
  - Review the spec with the add-on and player designs in hand, before calling it 0.1.
  - Try the example in the Babylon.js sandbox and the Khronos Sample Viewer, to confirm that the
    graph and node visibility behave there.
- **As built:**
  - The example's export is plain Blender 5.1 glTF, plus a post-pass for what the exporter can't
    write: the HVYM extensions, KHR_node_visibility, the unused paint material and the graph.
  - Validation rule 10, "the file shows the defaults", caught a real bug on its first run: Blender
    exported the Smile morph at weight 1 while `mood` defaults to 0.
  - Renders of three states (default; top hat, blue paint, full smile, blue lamp; half smile with
    the lamp off) matched what the state asked for.

### Phase 2: the Blender add-on

- A Blender 4.2+ extension, GPL-3.0-or-later, in `addon/`.
- **Panels:** properties, bindings, sets, controls, panels, and action recipes compiled to graphs.
- **Export:** through the glTF exporter's hooks. It applies the defaults first, keeps set materials,
  and validates.
- **Preview:** apply a state in the viewport.
- Replaces `make_example.py`'s post-pass. The example is then rebuilt with the add-on.
- Tests run in Blender, as Polyface's do, and renders are checked by eye.

### Phase 3: the player

- `<hvym-model>`, a web component, MIT, published to npm.
- **Does:** loads and validates the asset, and applies state and bindings.
- **Runs:** controls with pointer events, panels, and graphs with the HVYM operations.
- **State:** local `view` state only. No ledger yet.
- A page on tools.heavymeta.art to drop a file in and play it.

### Phase 4: ownership on testnet

- The collection contract and the factory ([OWNERSHIP.md](OWNERSHIP.md)), on OpenZeppelin
  `stellar-tokens`.
- Rent measured by simulation.
- The indexer.
- **The player:** reads copies and submits changes through a wallet.
- **Publishing:** pin to IPFS through Pintheon, from the add-on or the portal.

### Phase 5: sales on mainnet

- `buy` in USDC with purchase choices, resale with royalties, and signed changes for games.
- An external review of the contract before mainnet.
- Buyers without USDC use the Stripe on-ramp from the entitlements design.

### Phase 6: Polyface characters

- Expression bindings to the face's morph targets, lines as animations, and audio (spec 0.2).
- A talking example character.

### Phase 7: games

- A Godot importer (`GLTFDocumentExtension`): properties as data, bindings, and controls.
- Then Unity, through UnityGLTF.
- An example game that is a delegate and raises `xp`.

### Phase 8: standardisation

- Register the `HVYM` prefix with Khronos (a GitHub issue).
- Once two implementations exist (the player and the Godot importer), propose `HVYM_asset` and
  `HVYM_node_control` as vendor extensions under `extensions/2.0/Vendor/`.

## Decisions made

| Date | Decision |
|---|---|
| 2026-10-18 | A new repo, `hvym-standard`. `heavymeta_standard` stays as the archive. |
| 2026-10-18 | The repo is public. Spec text is CC BY 4.0. Schemas, tools and the player are MIT. The add-on is GPL-3.0-or-later. |
| 2026-10-18 | Start the format spec now, in parallel with Polyface's launch. |
| 2026-10-18 | glTF, not USD. Behaviour is KHR_interactivity, and HVYM adds only properties, rules, bindings, sets, panels and controls. |
| 2026-10-18 | References are glTF indices; properties and sets are referenced by name in HVYM data and by index in graphs. |
| 2026-10-18 | Price, supply and owners live in the contract, not the file. |
| 2026-10-18 | Ownership on Stellar Soroban, SEP-50, built on OpenZeppelin `stellar-tokens`. The format itself stays chain-neutral. |

## Open decisions

1. **The player's engine.** Babylon.js is recommended, since it plays KHR_interactivity today. The
   alternative is three.js plus our own graph interpreter.
2. **One contract per collection or one shared contract.** Per-collection is recommended
   ([OWNERSHIP.md](OWNERSHIP.md)).
3. **Plain transfers.** Always allowed, or a per-collection "sale only" option that enforces
   royalties but breaks some wallets?
4. **Delegates.** Collection-wide, or scoped per property? Can the creator remove one at any time?
5. **The co-op's role.** Gate the factory on membership? Take a share of sales or a creation fee?
6. **Purchase choices.** Are surcharges per option enough, or do creators want per-property pricing
   rules?
7. **Text on controls.** How a `text` control renders a string on a mesh: an SDF font on a plane
   fitted to the mesh, or a texture.
8. **Audio**, for Polyface lines: our own reference now, mapped to KHR_audio_emitter or
   KHR_audio_graph when one is ratified.

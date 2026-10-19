# Heavymeta Standard: agent guide

Programmable 3D assets: an open glTF format (`HVYM_asset`, `HVYM_node_control`), a Blender
add-on to author it, a web player, and Soroban contracts for owned copies. **Read
`docs/PLAN.md` first** for what's built, what's next and the open decisions. Then read
`docs/VISION.md` for the why, and `spec/HVYM_asset.md` for the format.

## Where things come from

- **The first Heavymeta Standard** (2022–2025, ICP) is the inspiration, not a code source.
  `docs/ORIGINAL.md` records it. Its repos are `inviti8/heavymeta_standard` (the add-on, MIT),
  `inviti8/heavymeta-cli-dev` (the CLI and the `hvym-proprium` runtime) and the template repos.
- **Polyface** (`D:\repos\polyface`) is the model for the add-on's structure and tests, and supplies
  talking characters.
- **Soroban contracts** live in `D:\repos\pintheon_contracts` (`inviti8/hvym_contracts`). Reuse its
  factory, registry and signed-payload patterns.
- **The entitlements design**, for card and USDC sales, is in
  `heavymeta_collective/docs/ENTITLEMENTS.md`.

## Rules for the format

- The spec, the schemas and `tools/validate.py` change together. Every validation rule in the spec
  has a check, and every check has a test in `tests/test_validate.py` that breaks the example.
- Build on Khronos extensions before inventing anything. HVYM defines only what's missing.
- Cite KHR_interactivity at a pinned registry commit; the text still changes after ratification.
- No chain specifics in the file. Price, supply and owners belong to the contract.

## Working here

- **Dev machine:** Windows 11, 16 GB RAM. Keep builds light.
- **Shells:** Bash is Git Bash. Heredocs break on some quote combinations, so write scripts and
  files with the editor tools, not `cat <<EOF`.
- **Deletes:** use literal paths, never `rm -rf "$VAR"`.
- **Blender:** run in the background with `--factory-startup`. Never install into the user's
  Blender while it's open.
- **Tests:** test what you build. For anything visual, render it (`tools/blender/preview.py`) and
  look. Say what was and wasn't verified.
- **Commits:** commit and push after each working phase, with messages that say what and why. End
  messages with the attribution line the session's instructions give.
- **The user tests by eye themselves.** When something needs their eyes, build it, say exactly how
  to try it, and ask.
- **Docs:** plain, direct sentences. Keep `docs/PLAN.md` current: mark phases built, add "As built"
  notes with anything measured, and record decisions as they're made.

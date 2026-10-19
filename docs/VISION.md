# Vision

## The idea in one paragraph

An artist makes a 3D character in Blender. Inside the file, alongside the mesh and the animations,
the character carries its own **properties**: a name the buyer chooses, a mood that drives the face,
experience that only ever goes up, a battery that only ever goes down. It also carries the **rules**
for each property: who may change it, in which direction and by how much. It carries its own
**behaviour** too: press the button on its chest and it waves. The file plays in any glTF viewer,
looking as authored. In a HEAVYMETA-aware player or game, it comes alive. When someone buys a copy,
that copy's properties live on a public ledger under the same rules, and the rules bind everyone,
the artist included. The buyer owns the copy, the artist is paid directly, and the asset keeps
working after any company behind it, ours included, is gone.

We call this a **programmable asset**. People have called the idea "NFTs on steroids". We avoid
that word in the product, but the comparison is fair: this is what NFTs promised and mostly didn't
deliver.

## Why now, and why this hasn't worked before

Digital 3D work is sold today as a file, or as a token that points at a file. Neither carries
behaviour or state. The "dynamic NFT" attempts of 2021–2023 mostly failed, for reasons we can
design against:

| What went wrong | What we do instead |
|---|---|
| Metadata and media sat on the project's servers and vanished with the project. | The asset is one open glTF file, addressed by its content hash on IPFS. The open player and the spec are public. |
| Admins could rewrite holders' traits; Racoon Secret Society did exactly that. | Each property's rule is fixed when the collection is created and enforced by the contract. Nobody can override it, the creator included. |
| State changed, but nothing rendered it consistently. | The file says how each property drives the scene (bindings), and behaviour is a standard Khronos graph. Any player can show the same thing. |
| Value depended on one game's servers or one oracle. | The asset is useful without any server: it renders, it animates, its owner can see and use it. Games add to it; they aren't required. |
| The pitch was speculation. | The pitch is the work: characters, props and objects that do things, sold by the people who made them. |

The timing works because the standards caught up:
- Khronos ratified **KHR_interactivity** (behaviour graphs in glTF) in August 2026.
- Node visibility, selectability and hoverability were ratified with it.
- Stellar's Soroban contracts make per-copy state cheap and rule-bound.
- The **SEP-50** NFT interface gives wallets and markets a common shape.

## Who it's for

- **Artists** who make characters, props and objects in Blender and want to sell them as more than
  a file.
- **Buyers** who want to own a thing that does something, and keep owning it.
- **Game and app makers** who want assets that arrive with their stats and behaviour already
  defined, in an open format.

## Principles

1. **The asset outlives its makers' servers.** The format, the schemas and the player are open.
   Media is content-addressed on IPFS. Ownership and state are on a public ledger. Nothing depends
   on HEAVYMETA being around.
2. **Rules travel with the asset, and bind everyone.** A property declares how it may change. The
   contract enforces the same rule. A creator can authorise a game to award experience, but can't
   make "experience only goes up" untrue.
3. **The creator owns their work and is paid directly.**
   - Collections are created and owned by the artist's own key.
   - Sales pay the artist's wallet in the same transaction.
   - HEAVYMETA never holds anyone's money or assets.
4. **Standards first.** Build on glTF, KHR_interactivity, KHR_node_visibility and SEP-50. HVYM adds
   only what's missing: properties, their rules, and how they drive the scene.
5. **Degrade gracefully.** The file renders correctly at its defaults in any glTF viewer. Each layer
   (properties, behaviour, ownership) adds to the one below and none is required.
6. **Plain language.** The interface says "your character", "edition 12 of 50", "experience". It
   doesn't say "NFT", "mint" or "on-chain" where an ordinary word will do.
7. **Open.**
   - The spec text is CC BY 4.0, like Khronos specs.
   - The schemas, tools and player are MIT.
   - The Blender add-on is GPL, as Blender requires of code that imports `bpy`.

## What it isn't

- Not a speculation platform. There's no token of our own in the asset format.
- Not a game engine. Games consume the format. The player is a viewer with interaction, not an
  engine.
- Not a metaverse. Assets go wherever their owners take them.
- Not tied to one chain in the format itself. The file describes properties and rules; the
  ownership design uses Stellar, and the format leaves room for other ledgers.

## Examples

- **A character.**
  - Made with Polyface: face rig, voice, lip-synced lines.
  - A `mood` property drives its expression.
  - Its owner names it when buying (`name`, chosen at purchase, then fixed).
  - `xp` only goes up, and only an authorised game can raise it.
  - Press its chest and it says hello.
- **A sword.**
  - `durability` only goes down. Its `edge` colour is picked at purchase, for a premium.
  - It glows according to `charge`, which its owner can top up.
- **A sculpture.**
  - Three colourways and a pedestal variant, chosen at purchase.
  - An edition of 50.
  - Each copy records its own provenance from the artist's key.

## Lineage

This is the second version of the **Heavymeta Standard**.
- The first was a Blender add-on, a CLI and a three.js runtime, built between 2022 and 2025 on the
  Internet Computer. It's at
  [inviti8/heavymeta_standard](https://github.com/inviti8/heavymeta_standard) and is now archived.
- Its authoring vocabulary was good, and most of it carries over: properties, mesh, material and
  morph sets, animations, actions, in-scene menus, and meshes that act as controls.
- What it lacked was a published format, rules the chain enforced, and a player that held up.

[ORIGINAL.md](ORIGINAL.md) records what it was and what we learned.

# Ownership: copies and their state on Stellar

A design, not yet built ([PLAN.md](PLAN.md), phases 4 and 5). It covers how a creator sells copies
of a template, how each copy's `mint` and `live` properties are stored, and how the property rules
are enforced so that nobody, the creator included, can break them.

## Goals

- **The creator owns the collection, and is paid directly.**
  - The contract is deployed by the creator's key.
  - Sales pay the creator in the same transaction.
  - HEAVYMETA has no admin power over it, and never holds funds.
- **Rules are fixed and enforced.**
  - The rule for each stored property is set when the collection is created, and can't be changed.
  - Every change is checked against it.
- **Standard where possible.**
  - Copies are SEP-50 NFTs, so Stellar wallets and markets can show and transfer them.
  - Built on OpenZeppelin's `stellar-tokens`, not hand-rolled.
- **It outlives us.**
  - Nothing requires a HEAVYMETA server.
  - Storage rent can be paid by anyone.
  - Archived state can be restored.

## Shape

- **One contract per collection.** A collection is one template, identified by its CID, plus its
  editions.
- **A factory deploys them.** The factory is registered in `hvym-registry` so clients can find it.
  The contract code is one audited Wasm, deployed many times. The salt is derived from the CID and
  the creator, so a collection's address is predictable.

### Why one contract per collection

- It's the creator's own contract.
- Its rules and its creator are its constructor arguments.
- Its address is the collection's identity in wallets.
- The cost: one deployment per collection, which is small next to a sale.

The alternative is one shared contract with collections inside it. That's cheaper to deploy, but it
blurs ownership and makes one contract a target for everything. It's still an open decision.

## The collection contract

Built on OpenZeppelin `stellar-tokens` (soroban-sdk 26 or newer):

- `non_fungible::Base`, the SEP-50 interface: `balance`, `owner_of`, `transfer`, `approve`, `name`,
  `symbol`, `token_uri`.
- Sequential token ids. Enumeration is left to the indexer, as OpenZeppelin suggests.
- The `royalties` extension for the royalty information, plus our own sale path that pays it.

### Constructor

| Argument | Meaning |
|---|---|
| `creator` | The creator's address. It authorises delegates and receives sales. |
| `template` | The template's CID. |
| `name`, `symbol` | The collection's name and symbol, for SEP-50. |
| `rules` | The rule table: one entry per stored property, in the file's order (below). |
| `supply` | The edition size. 0 means open. |
| `price` | The price in USDC, in 7-decimal units. |
| `pay_token` | The USDC Stellar Asset Contract address. |
| `choice_prices` | Optional surcharges for particular `mint` choices, such as 5 USDC for the blue paint. |
| `royalty_bps` | The royalty on resales, in basis points. |
| `coop` | Optional: a co-op address and its share in basis points. |

### The rule table

The table is derived from the template's `HVYM_asset.properties`. It keeps the `mint` and `live`
properties, in file order:

```rust
struct Rule {
    name: Symbol,          // the property's name: ≤ 32 chars, so it fits a Symbol
    kind: Kind,            // Bool | Int | Float | Color | Choice | Str
    lifetime: Lifetime,    // Mint | Live
    min: i128, max: i128,  // the range, scaled for floats; options - 1 for Choice; max bytes for Str
    default: Value,
    change: Change,        // None (mint) | Set | Increase | Decrease | Step
    amount: i128,          // 0 = any size
    by: u32,               // bit flags: OWNER | CREATOR | DELEGATE
}
```

- Anyone can check that the table matches the file: derive it from the file and compare.
- The player does this before trusting a collection.
- A mismatch means the collection isn't what the file says, and the player shows a warning.

### Values

Each copy's values are stored in **one persistent entry**, `Values(token_id)`. It holds a `Vec<Value>`
in rule-table order. One entry means one read per render and one TTL to manage.

| Type | Stored as |
|---|---|
| `bool` | 0 / 1 |
| `int` | `i128` |
| `float` | `i128`, the value × 10^`decimals` |
| `choice` | the option index |
| `color` | `u32`, sRGB 8 bits per channel, `0xRRGGBBAA` |
| `string` | `String`, at most `maxLength` bytes |

### Functions

| Function | Who | What |
|---|---|---|
| `buy(buyer, choices)` | anyone | Pays `price` plus the chosen surcharges, in USDC, to the creator (minus the co-op share). Mints the next copy to `buyer`, with `mint` values from `choices` (checked against the range and options) or the defaults, and `live` values at their defaults. Refused after `supply`. |
| `values(token_id)` | read | The copy's values. |
| `change(caller, token_id, index, op, arg)` | owner, creator or delegate | `op` is `Set(value)`, `Add(delta)` or `Sub(delta)`. It checks that the property is `live`, that `caller` is allowed by `by` and has authorised the call, that the op matches `change`, that `amount` is matched if it's set, and that the result is within range. The value is never clamped: an out-of-range result is refused. |
| `change_signed(payload, signature)` | anyone submits | The same change, authorised by an off-chain signature of the owner or a delegate. Games and apps can then relay changes and pay the fee. |
| `add_delegate(addr)`, `remove_delegate(addr)` | creator | Who counts as `delegate`. |
| `list(token_id, price)`, `unlist(token_id)` | owner | Puts a copy up for resale through the contract. |
| `buy_listed(buyer, token_id)` | anyone | Pays the listing price, sends the royalty to the creator and the rest to the seller, then transfers the copy. Its values move with it. |
| `extend(token_id)` | anyone | Extends the TTL of the copy's owner and values entries (rent). |
| `rules()`, `template()`, `creator()` | read | For players to verify against the file. |

There is **no** function that sets a value outside the rules, changes the rules, or changes the
template. That's what "no admin override" means in practice.

### Signed changes

`change_signed` follows the pattern of `hvym-cert-registry`:
- **The payload** is a canonical, sorted-key JSON. The contract rebuilds it from the call arguments
  and compares it byte for byte.
- **What it carries:**
  - an intent tag;
  - the collection;
  - `token_id`, `index`, `op` and `arg`;
  - a per-signer nonce;
  - an expiry ledger.
- **Signature:** SEP-53 (Stellar message signing). It is verified with `ed25519_verify`.

With this, a game server can award experience without its players holding XLM.

### Events

- **Standard:** SEP-50 `transfer`, `approve` and `mint`.
- **`("hvym_value", token_id)`** with `(index, old, new, by)` on every change. This is the
  equivalent of ERC-7496's `TraitUpdated`.
- **`("hvym_sale", token_id)`** with `(price, royalty, seller, buyer)` on resales.

### Rent and archival

- **Instance storage:** the configuration and the rule table. They're small, and they share the
  contract's TTL.
- **Persistent storage:** each copy's owner and values. Every write extends them by 30 days, as
  OpenZeppelin does, and `extend` lets anyone prepay up to the network maximum (about 180 days).
- **Archival is not loss.** An idle copy's entries are archived and restored automatically, for a
  fee, on next use (Protocol 23 and later). The player shows "restoring" rather than failing.
- **To do:** measure the rent per copy by simulation before fixing the TTL constants.
  `opus_token/src/rent_tests.rs` in `hvym_contracts` shows how.

## The factory

| Function | What |
|---|---|
| `create(creator, template, name, symbol, rules, supply, price, choice_prices, royalty_bps)` | The creator authorises the call. It deploys a collection contract (salt = hash(template, creator)), records it, and emits `("collection", creator)`. |
| `collections(creator)`, `collection(template, creator)` | Lookups. The indexer keeps the full list. |

- The factory may be gated on co-op membership and charge a creation fee. `hvym-collective`'s
  `deploy_ipfs_token` does both, and could do the same here.
- That's a business decision, recorded in [PLAN.md](PLAN.md).

## What the player does with all this

1. Read `copy="stellar:<collection>:<token>"`.
2. Fetch `template()` and `rules()` from the contract. Check that the template CID matches the file
   being shown, and that the rules match the ones derived from it.
3. Read `values(token_id)` through the indexer, falling back to the contract.
4. Apply the values over the defaults, then the bindings.
5. When someone changes a stored property, through a control, a panel or a graph:
   - check the rules locally, so obvious refusals don't reach the wallet;
   - build the `change` call and ask the host's wallet to sign it;
   - wait for the event, then update.

## Security notes

- **The creator can add delegates.** A delegate is still bound by every rule, so the worst case is a
  delegate raising `xp` to its maximum, within the rule. Creators should give delegate authority
  only to properties where that's acceptable. An open decision is whether delegates are scoped per
  property.
- **Plain `transfer` skips royalties.** It's kept so gifts and wallets work. A creator who wants
  royalties enforced on every move could choose a "sale only" collection. That's an open decision:
  it breaks some wallets.
- **No upgradeability.** Collection contracts aren't upgradeable. A fixed, audited Wasm is part of
  the trust model. The factory can deploy a newer version for new collections.
- **Before mainnet:** prices in 7-decimal USDC units, i128 arithmetic with overflow checks, and an
  external review of the contract.

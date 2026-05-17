# Loot (for Adventurers) — Complete Item & Rarity Analysis

**Collection:** 8,000 NFTs on Ethereum  
**Contract:** `0xff9c1b15b16263c61d017ee9f65c50e4ae0113d7`  
**Total item slots across collection:** 64,000 (8 slots × 8,000 bags)

---

## How Items Are Generated

Each bag is produced by a `pluck()` function seeded from `keccak256(slotName + tokenId)`. From that single random number, five values are derived:

| Derived Value | Formula | Range |
|---|---|---|
| Base item | `rand % items.length` | 0 → N−1 |
| Greatness | `rand % 21` | 0 → 20 |
| Suffix | `rand % 16` | 0 → 15 |
| Name prefix | `rand % 68` | 0 → 67 |
| Name suffix | `rand % 18` | 0 → 17 |

### Item Format Rules

| Greatness | Format | Probability |
|---|---|---|
| 0 – 14 | `Item` | 15/21 ≈ **71.4%** |
| 15 – 18 | `Item of Suffix` | 4/21 ≈ **19.0%** |
| 19 | `"Prefix NameSuffix" Item of Suffix` | 1/21 ≈ **4.8%** |
| 20 | `"Prefix NameSuffix" Item of Suffix +1` | 1/21 ≈ **4.8%** |

Named items (greatness 19–20) always also carry a suffix from the greatness > 14 branch.

---

## Rarity Tiers

Rarity is determined by how many times a **complete item string** (including all modifiers) appears across all 8,000 bags.

| Tier | Name | Occurrence Count | Share of All Items |
|---|---|---|---|
| 1 | **Common** | ≥ 375 | ~47% |
| 2 | **Uncommon** | 75 – 374 | ~13% |
| 3 | **Rare** | 11 – 74 | ~12% |
| 4 | **Epic** | 2 – 10 | ~10% |
| 5 | **Legendary** | 2 – 9 (named items) | ~10% |
| 6 | **Mythic** | exactly 1 | ~8% |

---

## Complete Item Catalog

### Slot 1 — Weapon (18 base items)

Each weapon is drawn for ~444 of the 8,000 bags.

| # | Item | Plain Occurrences* | Tier |
|---|---|---|---|
| 1 | Warhammer | ~317 | Uncommon |
| 2 | Quarterstaff | ~317 | Uncommon |
| 3 | Maul | ~317 | Uncommon |
| 4 | Mace | ~317 | Uncommon |
| 5 | Club | ~317 | Uncommon |
| 6 | Katana | ~317 | Uncommon |
| 7 | Falchion | ~317 | Uncommon |
| 8 | Scimitar | ~317 | Uncommon |
| 9 | Long Sword | ~317 | Uncommon |
| 10 | Short Sword | ~317 | Uncommon |
| 11 | Ghost Wand | ~317 | Uncommon |
| 12 | Grave Wand | ~317 | Uncommon |
| 13 | Bone Wand | ~317 | Uncommon |
| 14 | Wand | ~317 | Uncommon |
| 15 | Grimoire | ~317 | Uncommon |
| 16 | Chronicle | ~317 | Uncommon |
| 17 | Tome | ~317 | Uncommon |
| 18 | Book | ~317 | Uncommon |

*Plain = no suffix, no name (greatness 0–14). Actual counts vary due to on-chain pseudo-randomness.

**Suffixed weapons** (e.g. `Katana of Power`): ~5 occurrences each → **Epic**  
**Named weapons** (e.g. `"Kraken Bane" Katana of Power`): 0–2 occurrences each → **Legendary / Mythic**  
**Named +1 weapons**: 0–1 occurrences each → **Mythic**

---

### Slot 2 — Chest Armor (15 base items)

Each chest piece drawn for ~533 of the 8,000 bags.

| # | Item | Plain Occurrences* | Tier |
|---|---|---|---|
| 1 | Divine Robe | ~381 | Common |
| 2 | Silk Robe | ~381 | Common |
| 3 | Linen Robe | ~381 | Common |
| 4 | Robe | ~381 | Common |
| 5 | Shirt | ~381 | Common |
| 6 | Demon Husk | ~381 | Common |
| 7 | Dragonskin Armor | ~381 | Common |
| 8 | Studded Leather Armor | ~381 | Common |
| 9 | Hard Leather Armor | ~381 | Common |
| 10 | Leather Armor | ~381 | Common |
| 11 | Holy Chestplate | ~381 | Common |
| 12 | Ornate Chestplate | ~381 | Common |
| 13 | Plate Mail | ~381 | Common |
| 14 | Chain Mail | ~381 | Common |
| 15 | Ring Mail | ~381 | Common |

**Suffixed chest** (e.g. `Divine Robe of Power`): ~6 occurrences each → **Epic**  
**Named chest** (e.g. `"Dragon Roar" Divine Robe of Power`): 0–1 → **Mythic**

---

### Slot 3 — Head Armor (15 base items)

| # | Item | Plain Occurrences* | Tier |
|---|---|---|---|
| 1 | Ancient Helm | ~381 | Common |
| 2 | Ornate Helm | ~381 | Common |
| 3 | Great Helm | ~381 | Common |
| 4 | Full Helm | ~381 | Common |
| 5 | Helm | ~381 | Common |
| 6 | Demon Crown | ~381 | Common |
| 7 | Dragon's Crown | ~381 | Common |
| 8 | War Cap | ~381 | Common |
| 9 | Leather Cap | ~381 | Common |
| 10 | Cap | ~381 | Common |
| 11 | Crown | ~381 | Common |
| 12 | Divine Hood | ~381 | Common |
| 13 | Silk Hood | ~381 | Common |
| 14 | Linen Hood | ~381 | Common |
| 15 | Hood | ~381 | Common |

**Suffixed head** (e.g. `Ancient Helm of Giants`): ~6 occurrences each → **Epic**  
**Named head**: 0–1 → **Mythic**

---

### Slot 4 — Waist Armor (15 base items)

| # | Item | Plain Occurrences* | Tier |
|---|---|---|---|
| 1 | Ornate Belt | ~381 | Common |
| 2 | War Belt | ~381 | Common |
| 3 | Plated Belt | ~381 | Common |
| 4 | Mesh Belt | ~381 | Common |
| 5 | Heavy Belt | ~381 | Common |
| 6 | Demonhide Belt | ~381 | Common |
| 7 | Dragonskin Belt | ~381 | Common |
| 8 | Studded Leather Belt | ~381 | Common |
| 9 | Hard Leather Belt | ~381 | Common |
| 10 | Leather Belt | ~381 | Common |
| 11 | Brightsilk Sash | ~381 | Common |
| 12 | Silk Sash | ~381 | Common |
| 13 | Wool Sash | ~381 | Common |
| 14 | Linen Sash | ~381 | Common |
| 15 | Sash | ~381 | Common |

**Suffixed waist**: ~6 occurrences each → **Epic**  
**Named waist**: 0–1 → **Mythic**

---

### Slot 5 — Foot Armor (15 base items)

| # | Item | Plain Occurrences* | Tier |
|---|---|---|---|
| 1 | Holy Greaves | ~381 | Common |
| 2 | Ornate Greaves | ~381 | Common |
| 3 | Greaves | ~381 | Common |
| 4 | Chain Boots | ~381 | Common |
| 5 | Heavy Boots | ~381 | Common |
| 6 | Demonhide Boots | ~381 | Common |
| 7 | Dragonskin Boots | ~381 | Common |
| 8 | Studded Leather Boots | ~381 | Common |
| 9 | Hard Leather Boots | ~381 | Common |
| 10 | Leather Boots | ~381 | Common |
| 11 | Divine Slippers | ~381 | Common |
| 12 | Silk Slippers | ~381 | Common |
| 13 | Wool Shoes | ~381 | Common |
| 14 | Linen Shoes | ~381 | Common |
| 15 | Shoes | ~381 | Common |

**Suffixed foot**: ~6 occurrences each → **Epic**  
**Named foot**: 0–1 → **Mythic**

---

### Slot 6 — Hand Armor (15 base items)

| # | Item | Plain Occurrences* | Tier |
|---|---|---|---|
| 1 | Holy Gauntlets | ~381 | Common |
| 2 | Ornate Gauntlets | ~381 | Common |
| 3 | Gauntlets | ~381 | Common |
| 4 | Chain Gloves | ~381 | Common |
| 5 | Heavy Gloves | ~381 | Common |
| 6 | Demon's Hands | ~381 | Common |
| 7 | Dragonskin Gloves | ~381 | Common |
| 8 | Studded Leather Gloves | ~381 | Common |
| 9 | Hard Leather Gloves | ~381 | Common |
| 10 | Leather Gloves | ~381 | Common |
| 11 | Divine Gloves | ~381 | Common |
| 12 | Silk Gloves | ~381 | Common |
| 13 | Wool Gloves | ~381 | Common |
| 14 | Linen Gloves | ~381 | Common |
| 15 | Gloves | ~381 | Common |

**Suffixed hand**: ~6 occurrences each → **Epic**  
**Named hand**: 0–1 → **Mythic**

---

### Slot 7 — Necklaces (3 base items)

Each necklace drawn for ~2,667 of the 8,000 bags — the most common slot.

| # | Item | Plain Occurrences* | Tier |
|---|---|---|---|
| 1 | Necklace | ~1,905 | Common |
| 2 | Amulet | ~1,905 | Common |
| 3 | Pendant | ~1,905 | Common |

Actual observed counts (from dhof-loot data):

| Item | Observed Count |
|---|---|
| Pendant | 1,957 |
| Necklace | 1,921 |
| Amulet | 1,811 |

**Suffixed necklaces** (e.g. `Amulet of Power`): ~32 occurrences each → **Rare**  
**Named necklaces**: 0–3 occurrences → **Legendary / Mythic**

---

### Slot 8 — Rings (5 base items)

Each ring drawn for ~1,600 of the 8,000 bags.

| # | Item | Plain Occurrences* | Tier |
|---|---|---|---|
| 1 | Gold Ring | ~1,143 | Common |
| 2 | Silver Ring | ~1,143 | Common |
| 3 | Bronze Ring | ~1,143 | Common |
| 4 | Platinum Ring | ~1,143 | Common |
| 5 | Titanium Ring | ~1,143 | Common |

Actual observed counts (from dhof-loot data):

| Item | Observed Count |
|---|---|
| Titanium Ring | 1,112 |
| Gold Ring | 1,093 |
| Silver Ring | 1,178 |
| Platinum Ring | 1,163 |
| Bronze Ring | 1,166 |

**Suffixed rings** (e.g. `Gold Ring of Power`): ~19 occurrences each → **Rare**  
**Named rings**: 0–2 occurrences → **Legendary / Mythic**

---

## Modifier Lists

### Suffixes (16 total)
Applied when greatness 15–20. Each suffix has equal 1/16 probability per suffixed draw.

| # | Suffix |
|---|---|
| 1 | of Power |
| 2 | of Giants |
| 3 | of Titans |
| 4 | of Skill |
| 5 | of Perfection |
| 6 | of Brilliance |
| 7 | of Enlightenment |
| 8 | of Protection |
| 9 | of Anger |
| 10 | of Rage |
| 11 | of Fury |
| 12 | of Vitriol |
| 13 | of the Fox |
| 14 | of Detection |
| 15 | of Reflection |
| 16 | of the Twins |

### Name Prefixes (68 total)
Applied when greatness 19–20. Becomes the first word of the quoted item name.

| # | Prefix | # | Prefix | # | Prefix | # | Prefix |
|---|---|---|---|---|---|---|---|
| 1 | Agony | 18 | Dread | 35 | Hate | 52 | Rune |
| 2 | Apocalypse | 19 | Doom | 36 | Havoc | 53 | Skull |
| 3 | Armageddon | 20 | Dusk | 37 | Honour | 54 | Sol |
| 4 | Beast | 21 | Eagle | 38 | Horror | 55 | Soul |
| 5 | Behemoth | 22 | Empyrean | 39 | Hypnotic | 56 | Sorrow |
| 6 | Blight | 23 | Fate | 40 | Kraken | 57 | Spirit |
| 7 | Blood | 24 | Foe | 41 | Loath | 58 | Storm |
| 8 | Bramble | 25 | Gale | 42 | Maelstrom | 59 | Tempest |
| 9 | Brimstone | 26 | Ghoul | 43 | Mind | 60 | Torment |
| 10 | Brood | 27 | Gloom | 44 | Miracle | 61 | Vengeance |
| 11 | Carrion | 28 | Glyph | 45 | Morbid | 62 | Victory |
| 12 | Cataclysm | 29 | Golem | 46 | Oblivion | 63 | Viper |
| 13 | Chimeric | 30 | Grim | 47 | Onslaught | 64 | Vortex |
| 14 | Corpse | 31 | Hate | 48 | Pain | 65 | Woe |
| 15 | Corruption | 32 | Havoc | 49 | Pandemonium | 66 | Wrath |
| 16 | Damnation | 33 | Honour | 50 | Phoenix | 67 | Light's |
| 17 | Death | 34 | Horror | 51 | Plague | 68 | Shimmering |

### Name Suffixes (18 total)
Applied when greatness 19–20. Becomes the second word of the quoted item name.

| # | Name Suffix | # | Name Suffix |
|---|---|---|---|
| 1 | Bane | 10 | Shadow |
| 2 | Root | 11 | Whisper |
| 3 | Bite | 12 | Shout |
| 4 | Song | 13 | Growl |
| 5 | Roar | 14 | Tear |
| 6 | Grasp | 15 | Peak |
| 7 | Instrument | 16 | Form |
| 8 | Glow | 17 | Sun |
| 9 | Bender | 18 | Moon |

---

## Rarity Summary by Item Format

| Format | Example | Approx. Occurrences | Tier |
|---|---|---|---|
| Plain necklace | `Amulet` | ~1,900 | Common |
| Plain ring | `Gold Ring` | ~1,100 | Common |
| Plain armor (15-item slots) | `Divine Robe` | ~381 | Common |
| Plain weapon | `Katana` | ~317 | **Uncommon** |
| Suffixed necklace | `Amulet of Power` | ~32 | **Rare** |
| Suffixed ring | `Gold Ring of Power` | ~19 | **Rare** |
| Suffixed armor | `Divine Robe of Power` | ~6 | **Epic** |
| Suffixed weapon | `Katana of Power` | ~5 | **Epic** |
| Named necklace | `"Kraken Bane" Amulet of Power` | 0–2 | **Legendary/Mythic** |
| Named ring | `"Kraken Bane" Gold Ring of Power` | 0–1 | **Mythic** |
| Named armor | `"Kraken Bane" Divine Robe of Power` | 0–1 | **Mythic** |
| Named weapon | `"Kraken Bane" Katana of Power` | 0–1 | **Mythic** |
| Named +1 (any slot) | `"Kraken Bane" Katana of Power +1` | 0–1 | **Mythic** |

---

## Theoretical Item Space

| Category | Count |
|---|---|
| Total base items | 101 (18+15+15+15+15+15+3+5) |
| Suffixes | 16 |
| Name prefixes | 68 |
| Name suffixes | 18 |
| Possible unique named+suffixed combos (per slot) | up to N × 16 × 68 × 18 = N × 19,584 |
| **Total theoretical unique item strings** | **>1,000,000** |
| **Actual distinct strings in 8,000 bags** | **~64,000** |

The vast majority of named item combinations are **theoretically possible but never appear** in the 8,000 bag collection — those are effectively unmintable within original Loot.

---

## Key Rarity Facts

- **Rarest bag ever observed:** Token #3043 — highest concentration of rare traits in the collection.
- **Mythic items make up ~8.4%** of all item slots (~5,377 items), each appearing exactly once.
- **Necklaces are structurally the most common** slot (only 3 base items) — plain necklaces appear ~1,900 times each.
- **Weapons are structurally the rarest** plain items — all 18 weapons are Uncommon (~317 plain occurrences each, below the 375 Common threshold).
- **"+1" items are among the rarest possible** — only greatness-20 draws (4.8% of all draws), and then also require a specific named combination to repeat.
- **"Divine Robe of the Fox"** is a documented example of a Mythic item — appears exactly once across all 8,000 bags.
- **Short Sword** (plain) appears ~325 times — confirmed below the 375 threshold (Uncommon).

---

## Sources

- [lootproject.com](https://www.lootproject.com) — Official project site
- [bpierre/loot-rarity — GitHub](https://github.com/bpierre/loot-rarity) — Rarity tier library and thresholds
- [Anish-Agnihotri/dhof-loot — GitHub](https://github.com/Anish-Agnihotri/dhof-loot) — Full collection stats and occurrence data
- [dhof's original Loot contract — GitHub Gist](https://gist.github.com/JofArnold/1227316f9a094a9b9bc17274e557a6a7) — Canonical item arrays
- [Loot contract on Etherscan](https://etherscan.io/address/0xff9c1b15b16263c61d017ee9f65c50e4ae0113d7) — On-chain source of truth
- [DappRadar — Ultimate Guide to Loot NFTs](https://dappradar.com/blog/the-ultimate-guide-to-loot-nfts)
- [How to value your Loot NFTs — Substack](https://ayzd.substack.com/p/how-to-value-your-loot-for-adventurers)

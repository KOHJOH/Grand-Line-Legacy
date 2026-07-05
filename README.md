# Grand Line Legacy — Real Sprint 6

Sprint 6 adds the Island/NPC living world layer on top of Sprint 5.

## New commands

- `/island` — current island details
- `/travelmenu` — connected routes
- `/travel destination_id` — travel to connected islands
- `/npcs` — local NPC list
- `/talknpc npc_id` — talk to NPCs and gain friendship
- `/shops` — local shops
- `/shop shop_id` — shop inventory
- `/buy shop_id item_id quantity` — buy items
- `/searchtreasure` — find unclaimed island treasure
- `/gather resource_id` — gather local resources

## New data files

- `data/islands.json` expanded to major world regions
- `data/island_details.json`
- `data/npcs.json`
- `data/shops.json`
- `data/treasures.json`

## New persistence tables

- `island_discoveries`
- `npc_relationships`
- `player_treasures`
- `world_event_log`

## Commit message

`Sprint 6 - Island NPC Living World Engine`

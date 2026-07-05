CREATE TABLE IF NOT EXISTS currency_ledger (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    amount BIGINT NOT NULL,
    reason TEXT NOT NULL DEFAULT 'system',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_currency_ledger_player ON currency_ledger(discord_id, created_at DESC);

CREATE TABLE IF NOT EXISTS market_listings (
    id BIGSERIAL PRIMARY KEY,
    seller_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    buyer_id BIGINT REFERENCES players(discord_id) ON DELETE SET NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price BIGINT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sold_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_market_active ON market_listings(status, created_at DESC);

CREATE TABLE IF NOT EXISTS crafting_log (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    recipe_id TEXT NOT NULL,
    result_item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    crafted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fishing_log (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    island_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    xp_gained INTEGER NOT NULL DEFAULT 0,
    caught_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fishing_player ON fishing_log(discord_id, caught_at DESC);

CREATE TABLE IF NOT EXISTS dungeon_runs (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    dungeon_id TEXT NOT NULL,
    room INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_dungeon_runs_active ON dungeon_runs(discord_id, status, started_at DESC);

CREATE TABLE IF NOT EXISTS island_unlocks (
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    island_id TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT 'progression',
    unlocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(discord_id, island_id)
);

CREATE TABLE IF NOT EXISTS player_checkpoints (
    discord_id BIGINT PRIMARY KEY REFERENCES players(discord_id) ON DELETE CASCADE,
    island_id TEXT NOT NULL DEFAULT 'Foosha Village',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ship_mission_log (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    mission_name TEXT NOT NULL,
    xp_gained INTEGER NOT NULL DEFAULT 0,
    beli_gained BIGINT NOT NULL DEFAULT 0,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raid_lobbies (
    id BIGSERIAL PRIMARY KEY,
    leader_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    raid_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'forming',
    party JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO island_unlocks(discord_id, island_id, reason)
SELECT discord_id, 'Foosha Village', 'starter'
FROM players
ON CONFLICT(discord_id, island_id) DO NOTHING;

INSERT INTO player_checkpoints(discord_id, island_id)
SELECT discord_id, current_island
FROM players
ON CONFLICT(discord_id) DO NOTHING;

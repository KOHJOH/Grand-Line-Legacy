CREATE TABLE IF NOT EXISTS east_blue_progress (
    discord_id BIGINT PRIMARY KEY,
    unlocked_islands TEXT DEFAULT 'foosha_village',
    story_flags JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS player_quests (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    quest_id TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    progress INTEGER DEFAULT 0,
    required INTEGER DEFAULT 1,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    UNIQUE(discord_id, quest_id)
);

CREATE TABLE IF NOT EXISTS player_battles (
    discord_id BIGINT PRIMARY KEY,
    enemy_id TEXT NOT NULL,
    enemy_hp INTEGER NOT NULL,
    player_hp INTEGER NOT NULL,
    turn INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS player_inventory (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    UNIQUE(discord_id, item_id)
);

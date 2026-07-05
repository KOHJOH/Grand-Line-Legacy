CREATE TABLE IF NOT EXISTS player_fruits (
    player_id BIGINT PRIMARY KEY,
    equipped_fruit TEXT,
    fruit_mastery INTEGER DEFAULT 1,
    fruit_xp INTEGER DEFAULT 0,
    awakened BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fruit_storage (
    id SERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL,
    fruit_id TEXT NOT NULL,
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fruit_spawns (
    id SERIAL PRIMARY KEY,
    fruit_id TEXT NOT NULL,
    island TEXT NOT NULL,
    spawned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    claimed_by BIGINT
);

CREATE TABLE IF NOT EXISTS player_haki (
    player_id BIGINT PRIMARY KEY,
    observation_level INTEGER DEFAULT 0,
    observation_xp INTEGER DEFAULT 0,
    armament_level INTEGER DEFAULT 0,
    armament_xp INTEGER DEFAULT 0,
    conqueror_level INTEGER DEFAULT 0,
    conqueror_xp INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS active_battles_v2 (
    player_id BIGINT PRIMARY KEY,
    enemy_id TEXT NOT NULL,
    enemy_hp INTEGER NOT NULL,
    player_hp INTEGER NOT NULL,
    cooldowns JSONB DEFAULT '{}'::jsonb,
    turn_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS owner_audit_log (
    id SERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL,
    action TEXT NOT NULL,
    target_id BIGINT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE players ADD COLUMN IF NOT EXISTS attack INTEGER DEFAULT 10;
ALTER TABLE players ADD COLUMN IF NOT EXISTS defense INTEGER DEFAULT 5;
ALTER TABLE players ADD COLUMN IF NOT EXISTS speed INTEGER DEFAULT 5;
ALTER TABLE players ADD COLUMN IF NOT EXISTS crit_chance NUMERIC DEFAULT 5;
ALTER TABLE players ADD COLUMN IF NOT EXISTS dodge_chance NUMERIC DEFAULT 3;

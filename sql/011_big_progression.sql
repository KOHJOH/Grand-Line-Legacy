-- Sprint 11: bigger MMO progression systems. Safe/idempotent.
ALTER TABLE players ADD COLUMN IF NOT EXISTS bounty BIGINT DEFAULT 0;
ALTER TABLE players ADD COLUMN IF NOT EXISTS faction TEXT DEFAULT 'Pirate';
ALTER TABLE players ADD COLUMN IF NOT EXISTS fame INTEGER DEFAULT 0;
ALTER TABLE players ADD COLUMN IF NOT EXISTS reputation INTEGER DEFAULT 0;
ALTER TABLE players ADD COLUMN IF NOT EXISTS crew TEXT DEFAULT 'None';

CREATE TABLE IF NOT EXISTS crews (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    captain_id BIGINT NOT NULL,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    treasury BIGINT DEFAULT 0,
    fame INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crew_members (
    crew_id INTEGER REFERENCES crews(id) ON DELETE CASCADE,
    discord_id BIGINT UNIQUE NOT NULL,
    role TEXT DEFAULT 'Member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (crew_id, discord_id)
);

CREATE TABLE IF NOT EXISTS player_achievements (
    discord_id BIGINT NOT NULL,
    achievement_id TEXT NOT NULL,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (discord_id, achievement_id)
);

CREATE TABLE IF NOT EXISTS player_professions (
    discord_id BIGINT NOT NULL,
    profession TEXT NOT NULL,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    total_actions INTEGER DEFAULT 0,
    last_action_at TIMESTAMP,
    PRIMARY KEY (discord_id, profession)
);

CREATE TABLE IF NOT EXISTS bounty_logs (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    amount BIGINT NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory_items (
    discord_id BIGINT NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER DEFAULT 0,
    PRIMARY KEY (discord_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_crews_captain ON crews(captain_id);
CREATE INDEX IF NOT EXISTS idx_bounty_logs_player ON bounty_logs(discord_id);

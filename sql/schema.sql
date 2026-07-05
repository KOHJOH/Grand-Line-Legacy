CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS players (
    discord_id BIGINT PRIMARY KEY,
    username TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    xp INTEGER NOT NULL DEFAULT 0,
    beli INTEGER NOT NULL DEFAULT 500,
    race TEXT NOT NULL DEFAULT 'Human',
    faction TEXT NOT NULL DEFAULT 'Independent',
    current_island TEXT NOT NULL DEFAULT 'Foosha Village',
    hp INTEGER NOT NULL DEFAULT 100,
    max_hp INTEGER NOT NULL DEFAULT 100,
    stamina INTEGER NOT NULL DEFAULT 100,
    max_stamina INTEGER NOT NULL DEFAULT 100,
    title TEXT NOT NULL DEFAULT 'Rookie',
    bounty BIGINT NOT NULL DEFAULT 0,
    crew_name TEXT NOT NULL DEFAULT 'None',
    devil_fruit TEXT NOT NULL DEFAULT 'None',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE players ADD COLUMN IF NOT EXISTS username TEXT NOT NULL DEFAULT 'Unknown Pirate';
ALTER TABLE players ADD COLUMN IF NOT EXISTS level INTEGER NOT NULL DEFAULT 1;
ALTER TABLE players ADD COLUMN IF NOT EXISTS xp INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN IF NOT EXISTS beli INTEGER NOT NULL DEFAULT 500;
ALTER TABLE players ADD COLUMN IF NOT EXISTS race TEXT NOT NULL DEFAULT 'Human';
ALTER TABLE players ADD COLUMN IF NOT EXISTS faction TEXT NOT NULL DEFAULT 'Independent';
ALTER TABLE players ADD COLUMN IF NOT EXISTS current_island TEXT NOT NULL DEFAULT 'Foosha Village';
ALTER TABLE players ADD COLUMN IF NOT EXISTS hp INTEGER NOT NULL DEFAULT 100;
ALTER TABLE players ADD COLUMN IF NOT EXISTS max_hp INTEGER NOT NULL DEFAULT 100;
ALTER TABLE players ADD COLUMN IF NOT EXISTS stamina INTEGER NOT NULL DEFAULT 100;
ALTER TABLE players ADD COLUMN IF NOT EXISTS max_stamina INTEGER NOT NULL DEFAULT 100;
ALTER TABLE players ADD COLUMN IF NOT EXISTS title TEXT NOT NULL DEFAULT 'Rookie';
ALTER TABLE players ADD COLUMN IF NOT EXISTS bounty BIGINT NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN IF NOT EXISTS crew_name TEXT NOT NULL DEFAULT 'None';
ALTER TABLE players ADD COLUMN IF NOT EXISTS devil_fruit TEXT NOT NULL DEFAULT 'None';
ALTER TABLE players ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE players ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS player_inventory (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    locked BOOLEAN NOT NULL DEFAULT FALSE,
    instance_id UUID DEFAULT gen_random_uuid(),
    durability INTEGER,
    max_durability INTEGER,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(discord_id, item_id)
);

CREATE TABLE IF NOT EXISTS player_equipment (
    discord_id BIGINT PRIMARY KEY REFERENCES players(discord_id) ON DELETE CASCADE,
    weapon_item_id TEXT,
    armor_item_id TEXT,
    accessory_1_item_id TEXT,
    accessory_2_item_id TEXT,
    tool_item_id TEXT,
    cosmetic_item_id TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS player_quests (
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    quest_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    progress JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(discord_id, quest_id)
);

CREATE TABLE IF NOT EXISTS boss_codex (
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    boss_id TEXT NOT NULL,
    defeats INTEGER NOT NULL DEFAULT 0,
    first_defeated_at TIMESTAMPTZ,
    last_defeated_at TIMESTAMPTZ,
    PRIMARY KEY(discord_id, boss_id)
);

CREATE TABLE IF NOT EXISTS loot_history (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    rewards JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS combat_sessions (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    boss_id TEXT NOT NULL,
    boss_hp INTEGER NOT NULL,
    boss_max_hp INTEGER NOT NULL,
    phase INTEGER NOT NULL DEFAULT 1,
    turn INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_combat_sessions_active ON combat_sessions(discord_id, status);

CREATE TABLE IF NOT EXISTS npc_battle_sessions (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    enemy_id TEXT NOT NULL,
    enemy_hp INTEGER NOT NULL,
    enemy_max_hp INTEGER NOT NULL,
    turn INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_npc_battle_sessions_active ON npc_battle_sessions(discord_id, status, started_at DESC);

CREATE TABLE IF NOT EXISTS fruit_registry (
    fruit_id TEXT PRIMARY KEY,
    owner_discord_id BIGINT REFERENCES players(discord_id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'available',
    spawned_island TEXT,
    obtained_at TIMESTAMPTZ,
    recirculates_at TIMESTAMPTZ,
    history JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS player_fruits (
    discord_id BIGINT PRIMARY KEY REFERENCES players(discord_id) ON DELETE CASCADE,
    fruit_id TEXT NOT NULL,
    mastery INTEGER NOT NULL DEFAULT 0,
    mastery_xp INTEGER NOT NULL DEFAULT 0,
    awakened BOOLEAN NOT NULL DEFAULT FALSE,
    awakening_progress JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_trained_at TIMESTAMPTZ,
    obtained_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fruit_cooldowns (
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    ability_id TEXT NOT NULL,
    ready_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY(discord_id, ability_id)
);

CREATE TABLE IF NOT EXISTS fruitdex_entries (
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    fruit_id TEXT NOT NULL,
    seen BOOLEAN NOT NULL DEFAULT TRUE,
    owned BOOLEAN NOT NULL DEFAULT FALSE,
    mastered BOOLEAN NOT NULL DEFAULT FALSE,
    awakened BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(discord_id, fruit_id)
);

CREATE TABLE IF NOT EXISTS player_haki (
    discord_id BIGINT PRIMARY KEY REFERENCES players(discord_id) ON DELETE CASCADE,
    observation_unlocked BOOLEAN NOT NULL DEFAULT FALSE,
    observation_level INTEGER NOT NULL DEFAULT 0,
    observation_xp INTEGER NOT NULL DEFAULT 0,
    armament_unlocked BOOLEAN NOT NULL DEFAULT FALSE,
    armament_level INTEGER NOT NULL DEFAULT 0,
    armament_xp INTEGER NOT NULL DEFAULT 0,
    conqueror_potential BOOLEAN NOT NULL DEFAULT FALSE,
    conqueror_unlocked BOOLEAN NOT NULL DEFAULT FALSE,
    conqueror_level INTEGER NOT NULL DEFAULT 0,
    conqueror_xp INTEGER NOT NULL DEFAULT 0,
    active_observation BOOLEAN NOT NULL DEFAULT FALSE,
    active_armament BOOLEAN NOT NULL DEFAULT FALSE,
    active_conqueror BOOLEAN NOT NULL DEFAULT FALSE,
    haki_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS haki_training_log (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    haki_type TEXT NOT NULL,
    xp_gained INTEGER NOT NULL,
    level_after INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS island_discoveries (
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    island_id TEXT NOT NULL,
    visits INTEGER NOT NULL DEFAULT 1,
    first_visited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_visited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    secrets_found JSONB NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY(discord_id, island_id)
);

CREATE TABLE IF NOT EXISTS npc_relationships (
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    npc_id TEXT NOT NULL,
    friendship INTEGER NOT NULL DEFAULT 0,
    talks INTEGER NOT NULL DEFAULT 0,
    flags JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_talked_at TIMESTAMPTZ,
    PRIMARY KEY(discord_id, npc_id)
);

CREATE TABLE IF NOT EXISTS player_treasures (
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    treasure_id TEXT NOT NULL,
    island_id TEXT NOT NULL,
    found_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(discord_id, treasure_id)
);

CREATE TABLE IF NOT EXISTS world_event_log (
    id BIGSERIAL PRIMARY KEY,
    island_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS world_news_articles (
    id BIGSERIAL PRIMARY KEY,
    headline TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    island_id TEXT,
    player_id BIGINT REFERENCES players(discord_id) ON DELETE SET NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_world_news_created_at ON world_news_articles(created_at DESC);

CREATE TABLE IF NOT EXISTS active_world_events (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL,
    name TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'Global',
    island_id TEXT NOT NULL DEFAULT 'global',
    event_type TEXT NOT NULL DEFAULT 'general',
    description TEXT NOT NULL,
    effects JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'active',
    started_by BIGINT REFERENCES players(discord_id) ON DELETE SET NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ends_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_active_world_events_status ON active_world_events(status, island_id, ends_at);

CREATE TABLE IF NOT EXISTS player_ships (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    ship_type TEXT NOT NULL,
    nickname TEXT NOT NULL,
    hull_hp INTEGER NOT NULL,
    max_hull_hp INTEGER NOT NULL,
    speed INTEGER NOT NULL,
    cargo_capacity INTEGER NOT NULL,
    crew_capacity INTEGER NOT NULL,
    cannon_slots INTEGER NOT NULL DEFAULT 0,
    upgrade_level INTEGER NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    purchased_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_player_ships_owner ON player_ships(discord_id, active);

CREATE TABLE IF NOT EXISTS ship_cargo (
    ship_id BIGINT NOT NULL REFERENCES player_ships(id) ON DELETE CASCADE,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(ship_id, item_id)
);

CREATE TABLE IF NOT EXISTS travel_sessions (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    origin_island TEXT NOT NULL,
    destination_island TEXT NOT NULL,
    ship_id BIGINT NOT NULL REFERENCES player_ships(id) ON DELETE CASCADE,
    duration_seconds INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'sailing',
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ends_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_travel_sessions_active ON travel_sessions(discord_id, status, ends_at);

CREATE TABLE IF NOT EXISTS ocean_encounter_log (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    travel_session_id BIGINT NOT NULL REFERENCES travel_sessions(id) ON DELETE CASCADE,
    encounter_id TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ocean_encounter_unresolved ON ocean_encounter_log(discord_id, resolved, created_at);

-- Sprint 16-20 cumulative systems: East Blue, NPC dialogue, skills, fruit spawns, sea routes.
CREATE TABLE IF NOT EXISTS island_discoveries (
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    island_id TEXT NOT NULL,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(discord_id, island_id)
);

CREATE TABLE IF NOT EXISTS npc_relationships (
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    npc_id TEXT NOT NULL,
    friendship INTEGER NOT NULL DEFAULT 0,
    talks INTEGER NOT NULL DEFAULT 0,
    flags JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(discord_id, npc_id)
);

CREATE TABLE IF NOT EXISTS player_skills (
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    skill_id TEXT NOT NULL,
    mastery INTEGER NOT NULL DEFAULT 1,
    xp INTEGER NOT NULL DEFAULT 0,
    equipped_slot INTEGER,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(discord_id, skill_id)
);

CREATE TABLE IF NOT EXISTS skill_cooldowns (
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    skill_id TEXT NOT NULL,
    ready_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY(discord_id, skill_id)
);

CREATE TABLE IF NOT EXISTS fruit_spawns (
    id BIGSERIAL PRIMARY KEY,
    fruit_id TEXT NOT NULL,
    fruit_name TEXT NOT NULL,
    island TEXT NOT NULL,
    rarity TEXT NOT NULL DEFAULT 'Rare',
    spawned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    claimed_by BIGINT REFERENCES players(discord_id) ON DELETE SET NULL,
    claimed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_fruit_spawns_active ON fruit_spawns(island, claimed_by, expires_at);

CREATE TABLE IF NOT EXISTS voyages (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    encounter_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_voyages_active ON voyages(discord_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS story_flags (
    discord_id BIGINT NOT NULL REFERENCES players(discord_id) ON DELETE CASCADE,
    flag_id TEXT NOT NULL,
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(discord_id, flag_id)
);

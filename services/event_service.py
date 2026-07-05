from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from services.news_service import NewsService


class EventService:
    """Manages active world events loaded from static JSON data."""

    def __init__(self, db, events: list[dict[str, Any]]) -> None:
        self.db = db
        self.events = {event["id"]: event for event in events}

    def list_event_templates(self, region: str | None = None, island_id: str | None = None) -> list[dict[str, Any]]:
        events = list(self.events.values())
        if region:
            events = [e for e in events if e.get("region", "").lower() == region.lower()]
        if island_id:
            events = [e for e in events if e.get("island_id") in {island_id, "global"}]
        return events

    async def active_events(self, island_id: str | None = None):
        if island_id:
            return await self.db.fetch(
                """
                SELECT * FROM active_world_events
                WHERE status = 'active'
                AND (island_id = $1 OR island_id = 'global')
                ORDER BY ends_at ASC
                """,
                island_id,
            )
        return await self.db.fetch(
            """
            SELECT * FROM active_world_events
            WHERE status = 'active'
            ORDER BY ends_at ASC
            """
        )

    async def start_event(self, event_id: str, *, started_by: int | None = None):
        event = self.events.get(event_id)
        if not event:
            raise ValueError(f"Unknown world event: {event_id}")
        now = datetime.now(timezone.utc)
        ends_at = now + timedelta(minutes=int(event.get("duration_minutes", 60)))
        row = await self.db.fetchrow(
            """
            INSERT INTO active_world_events
                (event_id, name, region, island_id, event_type, description, effects, status, started_by, started_at, ends_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, 'active', $8, $9, $10)
            RETURNING *
            """,
            event["id"],
            event["name"],
            event.get("region", "Global"),
            event.get("island_id", "global"),
            event.get("type", "general"),
            event.get("description", ""),
            event.get("effects", {}),
            started_by,
            now,
            ends_at,
        )
        await self.db.execute(
            """
            INSERT INTO world_event_log (island_id, event_type, description, payload)
            VALUES ($1, $2, $3, $4::jsonb)
            """,
            event.get("island_id", "global"),
            event.get("type", "general"),
            f"Started: {event['name']}",
            {"event_id": event["id"], "active_event_id": row["id"]},
        )
        if event.get("newsworthy", False):
            await NewsService(self.db).publish_system_news(event, started=True)
        return row

    async def end_event(self, active_event_id: int):
        row = await self.db.fetchrow(
            """
            UPDATE active_world_events
            SET status = 'ended', ended_at = NOW()
            WHERE id = $1 AND status = 'active'
            RETURNING *
            """,
            active_event_id,
        )
        if row:
            event = self.events.get(row["event_id"], {})
            if event.get("newsworthy", False):
                await NewsService(self.db).publish_system_news(event, started=False)
        return row

    async def cleanup_expired(self) -> int:
        rows = await self.db.fetch(
            """
            UPDATE active_world_events
            SET status = 'ended', ended_at = NOW()
            WHERE status = 'active' AND ends_at <= NOW()
            RETURNING id
            """
        )
        return len(rows)

    async def roll_random_event(self, *, island_id: str | None = None):
        pool = self.list_event_templates(island_id=island_id)
        if not pool:
            pool = list(self.events.values())
        return await self.start_event(random.choice(pool)["id"])

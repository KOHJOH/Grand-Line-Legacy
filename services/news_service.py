from __future__ import annotations

from typing import Any


class NewsService:
    """Stores and retrieves World News articles.

    This service is intentionally small right now. Later systems can call
    publish_article from boss defeats, fruit awakenings, faction wars, and raids.
    """

    def __init__(self, db) -> None:
        self.db = db

    async def publish_article(
        self,
        *,
        headline: str,
        body: str,
        category: str = "general",
        island_id: str | None = None,
        player_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ):
        return await self.db.fetchrow(
            """
            INSERT INTO world_news_articles
                (headline, body, category, island_id, player_id, payload)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            RETURNING *
            """,
            headline,
            body,
            category,
            island_id,
            player_id,
            payload or {},
        )

    async def latest(self, limit: int = 10):
        return await self.db.fetch(
            """
            SELECT * FROM world_news_articles
            ORDER BY created_at DESC
            LIMIT $1
            """,
            max(1, min(limit, 25)),
        )

    async def get_article(self, article_id: int):
        return await self.db.fetchrow(
            "SELECT * FROM world_news_articles WHERE id = $1",
            article_id,
        )

    async def publish_system_news(self, event: dict[str, Any], *, started: bool = True):
        verb = "has begun" if started else "has ended"
        headline = f"{event['name']} {verb}"
        body = event.get("description", "A world event has changed the seas.")
        return await self.publish_article(
            headline=headline,
            body=body,
            category="world_event",
            island_id=event.get("island_id"),
            payload={"event_id": event.get("id"), "started": started},
        )

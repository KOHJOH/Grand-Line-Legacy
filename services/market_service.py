from __future__ import annotations

from core.database import Database
from services.inventory_ops import InventoryOps
from services.wallet_service import WalletService


class MarketService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.inv = InventoryOps(db)
        self.wallet = WalletService(db)

    async def listings(self, limit: int = 10):
        return await self.db.fetch(
            """
            SELECT * FROM market_listings
            WHERE status='active'
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )

    async def create_listing(self, seller_id: int, item_id: str, quantity: int, price: int) -> tuple[bool, str]:
        quantity = max(1, int(quantity))
        price = max(1, int(price))
        if not await self.inv.remove_item(seller_id, item_id, quantity):
            return False, "You don't have enough of that item."
        row = await self.db.fetchrow(
            """
            INSERT INTO market_listings(seller_id, item_id, quantity, price)
            VALUES($1,$2,$3,$4)
            RETURNING id
            """,
            seller_id,
            item_id,
            quantity,
            price,
        )
        return True, f"Listed `{item_id}` x{quantity} for {price:,} Beli. Listing ID: `{row['id']}`"

    async def buy_listing(self, buyer_id: int, listing_id: int) -> tuple[bool, str]:
        listing = await self.db.fetchrow("SELECT * FROM market_listings WHERE id=$1 AND status='active'", int(listing_id))
        if not listing:
            return False, "That listing is not active."
        if int(listing["seller_id"]) == buyer_id:
            return False, "You can't buy your own listing."
        ok, balance = await self.wallet.spend(buyer_id, int(listing["price"]), "market_purchase")
        if not ok:
            return False, f"Not enough Beli. Current balance: {balance:,}."
        await self.wallet.add(int(listing["seller_id"]), int(listing["price"]), "market_sale")
        await self.inv.add_item(buyer_id, listing["item_id"], int(listing["quantity"]))
        await self.db.execute("UPDATE market_listings SET status='sold', buyer_id=$2, sold_at=NOW() WHERE id=$1", int(listing_id), buyer_id)
        return True, f"Purchased `{listing['item_id']}` x{listing['quantity']} for {int(listing['price']):,} Beli."

    async def cancel_listing(self, seller_id: int, listing_id: int) -> tuple[bool, str]:
        listing = await self.db.fetchrow("SELECT * FROM market_listings WHERE id=$1 AND status='active'", int(listing_id))
        if not listing or int(listing["seller_id"]) != seller_id:
            return False, "Listing not found or not yours."
        await self.inv.add_item(seller_id, listing["item_id"], int(listing["quantity"]))
        await self.db.execute("UPDATE market_listings SET status='cancelled', sold_at=NOW() WHERE id=$1", int(listing_id))
        return True, "Listing cancelled and item returned."

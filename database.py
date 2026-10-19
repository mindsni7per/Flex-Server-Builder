import aiosqlite
import time
from config import DATABASE_FILE, DAILY_USAGE_LIMIT

class Database:
    @staticmethod
    async def init_db():
        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS usage (
                    user_id INTEGER PRIMARY KEY,
                    count INTEGER DEFAULT 0,
                    last_reset REAL
                )
            """)
            await db.commit()

    @staticmethod
    async def check_and_increment_usage(user_id: int) -> tuple[bool, int, float]:
        """
        Returns (can_use: bool, current_usage: int, time_until_reset_seconds: float)
        """
        now = time.time()
        day_in_seconds = 86400

        async with aiosqlite.connect(DATABASE_FILE) as db:
            async with db.execute("SELECT count, last_reset FROM usage WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()

            if row is None:
                # First time user
                await db.execute("INSERT INTO usage (user_id, count, last_reset) VALUES (?, 1, ?)", (user_id, now))
                await db.commit()
                return True, 1, 86400.0

            count, last_reset = row
            if now - last_reset >= day_in_seconds:
                # 24 hours passed, reset counter
                await db.execute("UPDATE usage SET count = 1, last_reset = ? WHERE user_id = ?", (now, user_id))
                await db.commit()
                return True, 1, 86400.0
            else:
                time_until_reset = day_in_seconds - (now - last_reset)
                if count < DAILY_USAGE_LIMIT:
                    new_count = count + 1
                    await db.execute("UPDATE usage SET count = ? WHERE user_id = ?", (new_count, user_id))
                    await db.commit()
                    return True, new_count, time_until_reset
                else:
                    return False, count, time_until_reset

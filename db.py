import aiosqlite
import datetime

DB_PATH = "user_data.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_subscribed INTEGER DEFAULT 0,
            free_until TIMESTAMP,
            has_unlimited INTEGER DEFAULT 0
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            days INTEGER,
            max_uses INTEGER,
            used_count INTEGER DEFAULT 0,
            unlimited INTEGER DEFAULT 0
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS promocode_usages (
            user_id INTEGER,
            code TEXT,
            used_at TIMESTAMP,
            PRIMARY KEY (user_id, code)
        )
        """)
        await db.commit()
        # Добавляем промокоды, если их нет
        await db.execute(
            "INSERT OR IGNORE INTO promocodes (code, days, max_uses, unlimited) VALUES (?, ?, ?, ?)",
            ("MARK01", 0, 50, 1)  # Вечный доступ, до 50 пользователей
        )
        await db.execute(
            "INSERT OR IGNORE INTO promocodes (code, days, max_uses, unlimited) VALUES (?, ?, ?, ?)",
            ("SWR25", 1, 10, 0)  # 24 часа (1 день), максимум 10 использований
        )
        await db.commit()

async def add_user(user_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, free_until) VALUES (?, ?, ?)",
            (user_id, username, datetime.datetime.now() + datetime.timedelta(days=7))
        )
        await db.commit()

async def set_subscription(user_id: int, is_subscribed: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_subscribed = ? WHERE user_id = ?",
            (1 if is_subscribed else 0, user_id)
        )
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def update_free_until(user_id: int, days: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET free_until = ? WHERE user_id = ?",
            (datetime.datetime.now() + datetime.timedelta(days=days), user_id)
        )
        await db.commit()

async def set_unlimited(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET has_unlimited = 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()

async def add_promocode(code: str, days: int, max_uses: int, unlimited: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO promocodes (code, days, max_uses, unlimited) VALUES (?, ?, ?, ?)",
            (code, days, max_uses, unlimited)
        )
        await db.commit()

async def use_promocode(user_id: int, code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем промокод
        async with db.execute("SELECT days, max_uses, used_count, unlimited FROM promocodes WHERE code = ?", (code,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False, "Промокод не найден"
            days, max_uses, used_count, unlimited = row
            if not unlimited and used_count >= max_uses:
                return False, "Промокод уже использован максимальное число раз"
        # Проверяем, использовал ли пользователь этот промокод ранее
        async with db.execute("SELECT 1 FROM promocode_usages WHERE user_id = ? AND code = ?", (user_id, code)) as cursor:
            if await cursor.fetchone():
                return False, "Вы уже использовали этот промокод"
        # Применяем промокод
        if unlimited:
            await set_unlimited(user_id)
        else:
            await update_free_until(user_id, days)
        await db.execute(
            "UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?",
            (code,)
        )
        await db.execute(
            "INSERT INTO promocode_usages (user_id, code, used_at) VALUES (?, ?, ?)",
            (user_id, code, datetime.datetime.now())
        )
        await db.commit()
        return True, "Промокод успешно применён"

async def check_access(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_subscribed, free_until, has_unlimited FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            is_subscribed, free_until, has_unlimited = row
            if has_unlimited:
                return True
            if is_subscribed and (free_until is None or datetime.datetime.fromisoformat(free_until) > datetime.datetime.now()):
                return True
            if free_until and datetime.datetime.fromisoformat(free_until) > datetime.datetime.now():
                return True
            return False
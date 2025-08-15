import aiosqlite
import datetime
import logging

DB_PATH = "user_data.db"

# Настройка логирования
logger = logging.getLogger(__name__)

async def init_db():
    """Инициализация базы данных (упрощенная версия)"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Упрощенная таблица пользователей
            await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                is_subscribed INTEGER DEFAULT 0
            )
            """)
            
            # Удаляем ненужные таблицы
            await db.execute("DROP TABLE IF EXISTS promocodes")
            await db.execute("DROP TABLE IF EXISTS promocode_usages")
            await db.execute("DROP TABLE IF EXISTS promo_history")
            
            await db.commit()
            logger.info("База данных успешно инициализирована (упрощенная версия)")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise

async def add_or_update_user(user_id: int, username: str):
    """Добавляет или обновляет пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )
            await db.commit()
            logger.info(f"Обновлен пользователь: {user_id} ({username})")
    except Exception as e:
        logger.error(f"Ошибка обновления пользователя {user_id}: {e}")

async def set_subscription(user_id: int, active: bool):
    """
    Устанавливает статус подписки на канал
    active: True - подписан, False - не подписан
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET is_subscribed = ? WHERE user_id = ?",
                (1 if active else 0, user_id)
            )
            await db.commit()
            logger.info(f"Обновлена подписка для {user_id}: статус={active}")
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления подписки {user_id}: {e}")
        return False

async def get_user(user_id: int):
    """Возвращает данные пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                return await cursor.fetchone()
    except Exception as e:
        logger.error(f"Ошибка получения пользователя {user_id}: {e}")
        return None

async def check_access(user_id: int) -> bool:
    """Проверяет доступ пользователя к боту (только подписка на канал)"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("""
                SELECT is_subscribed 
                FROM users 
                WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    logger.info(f"Пользователь {user_id} не найден при проверке доступа")
                    return False
                
                is_subscribed = row[0]
                return bool(is_subscribed)
    except Exception as e:
        logger.error(f"Ошибка проверки доступа для {user_id}: {e}")
        return False
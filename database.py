"""
Gestor de Base de Datos SQLite Asíncrono para Ben Informante.
Registra usuarios, consultas de IA realizadas y estado de membresía.
"""
import aiosqlite
import os
import datetime
from config import DB_PATH

async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                questions_used INTEGER DEFAULT 0,
                is_pro INTEGER DEFAULT 0,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def upsert_user(user_id: int, username: str, first_name: str):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, last_active)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_active = excluded.last_active
        """, (user_id, username or "", first_name or "", now))
        await db.commit()

async def get_user(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {
                "user_id": user_id,
                "questions_used": 0,
                "is_pro": 0
            }

async def increment_question(user_id: int) -> int:
    """Incrementa las preguntas usadas y retorna el nuevo total."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users
            SET questions_used = questions_used + 1,
                last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (user_id,))
        await db.commit()
    user = await get_user(user_id)
    return user.get("questions_used", 0)

async def set_pro_status(user_id: int, is_pro: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_pro = ? WHERE user_id = ?", (1 if is_pro else 0, user_id))
        await db.commit()

async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*), SUM(questions_used), SUM(is_pro) FROM users") as cursor:
            total_users, total_questions, total_pro = await cursor.fetchone()
            return {
                "total_users": total_users or 0,
                "total_questions": total_questions or 0,
                "total_pro": total_pro or 0
            }

"""Base de datos SQLite asíncrona para el bot PDF."""
import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id   INTEGER PRIMARY KEY,
            username  TEXT,
            first_name TEXT,
            joined_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS operations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            op_type    TEXT,
            file_name  TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)
        await db.commit()

async def upsert_user(uid, username, first_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users(user_id,username,first_name)
            VALUES(?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name
        """, (uid, username or "", first_name or ""))
        await db.commit()

async def log_operation(user_id: int, op_type: str, file_name: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO operations(user_id,op_type,file_name) VALUES(?,?,?)",
            (user_id, op_type, file_name)
        )
        await db.commit()

async def get_user_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        total = await db.execute_fetchall(
            "SELECT op_type, COUNT(*) as n FROM operations WHERE user_id=? GROUP BY op_type",
            (user_id,)
        )
        count = await db.execute_fetchall(
            "SELECT COUNT(*) as n FROM operations WHERE user_id=?", (user_id,)
        )
    return {
        "by_type": {r["op_type"]: r["n"] for r in total},
        "total": count[0]["n"] if count else 0
    }

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        return await db.execute_fetchall("SELECT * FROM users")

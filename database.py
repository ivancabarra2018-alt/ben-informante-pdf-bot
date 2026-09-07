"""
Base de datos SQLite asíncrona para Accede Gratis Tipster VIP.
Gestiona usuarios, pronósticos reales y estado del partido del día.
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
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS picks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_title TEXT,
                competition TEXT,
                match_time TEXT,
                selection TEXT,
                odds REAL,
                stake REAL,
                analysis TEXT,
                status TEXT DEFAULT 'PENDIENTE', -- PENDIENTE, ACERTADO, FALLADO
                notified_win INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

        # Asegurar el partido real de hoy como activo
        await setup_real_match_of_the_day(db)

async def setup_real_match_of_the_day(db):
    """Configura el partido real de hoy (Getafe vs Celta de Vigo - LaLiga)."""
    async with db.execute("SELECT id FROM picks WHERE match_title LIKE '%Getafe%'") as cursor:
        existing = await cursor.fetchone()
        if not existing:
            # Desactivar anteriores
            await db.execute("UPDATE picks SET is_active = 0")
            # Insertar partido real de hoy
            await db.execute("""
                INSERT INTO picks (match_title, competition, match_time, selection, odds, stake, analysis, status, is_active, notified_win)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDIENTE', 1, 0)
            """, (
                "Getafe CF vs RC Celta de Vigo",
                "LaLiga EA Sports",
                "Hoy a las 19:00 (Hora local)",
                "Menos de 2.5 Goles",
                1.65,
                1.5,
                "Encuentro de alta rigidez táctica en el Coliseum. El Getafe de Bordalás prioriza el orden defensivo en bloque bajo (concede un xG inferior a 0.9 en casa). Por su parte, el Celta presenta dificultades de eficacia fuera de Balaídos. Nuestros modelos estadísticos sitúan la probabilidad de menos de 2.5 goles en un 68% frente a la cuota 1.65 del mercado (+EV claro)."
            ))
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

async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def get_active_pick() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM picks WHERE is_active = 1 ORDER BY id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            async with db.execute("SELECT * FROM picks ORDER BY id DESC LIMIT 1") as c2:
                r2 = await c2.fetchone()
                return dict(r2) if r2 else {}

async def mark_active_pick_won(pick_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("UPDATE picks SET status = 'ACERTADO', notified_win = 1 WHERE id = ?", (pick_id,))
        await db.commit()
        async with db.execute("SELECT * FROM picks WHERE id = ?", (pick_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}

async def set_new_active_pick(match_title: str, competition: str, match_time: str, selection: str, odds: float, stake: float, analysis: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE picks SET is_active = 0")
        await db.execute("""
            INSERT INTO picks (match_title, competition, match_time, selection, odds, stake, analysis, status, is_active, notified_win)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDIENTE', 1, 0)
        """, (match_title, competition, match_time, selection, odds, stake, analysis))
        await db.commit()

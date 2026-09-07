"""
Base de datos SQLite asíncrona para Accede Gratis Pro.
Gestiona usuarios, administradores, pronósticos reales (gratuito y siguiente de pago),
justificantes de pago enviados, reseteos de acceso y compensación por fallo.
"""
import aiosqlite
import os
import datetime
from config import DB_PATH, DEFAULT_PAYMENT_URL

async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                is_admin INTEGER DEFAULT 0,
                has_paid_access INTEGER DEFAULT 0,
                has_seen_free_pick INTEGER DEFAULT 0,
                paid_count INTEGER DEFAULT 0,
                consumed_free_victory INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migraciones para tablas existentes
        try:
            await db.execute("ALTER TABLE users ADD COLUMN paid_count INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN consumed_free_victory INTEGER DEFAULT 0")
        except Exception:
            pass

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
                is_vip_next INTEGER DEFAULT 0,    -- 0: gratis de hoy, 1: siguiente de pago
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                photo_file_id TEXT,
                ai_analysis TEXT,
                status TEXT DEFAULT 'PENDIENTE', -- PENDIENTE, APROBADO, RECHAZADO
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.commit()

        # Configurar enlace de pago por defecto si no existe
        async with db.execute("SELECT value FROM settings WHERE key = 'payment_url'") as cursor:
            row = await cursor.fetchone()
            if not row:
                await db.execute("INSERT INTO settings (key, value) VALUES ('payment_url', ?)", (DEFAULT_PAYMENT_URL,))
                await db.commit()

        # Configurar / actualizar partidos reales
        await seed_or_update_real_picks(db)

async def seed_or_update_real_picks(db):
    # Desactivar picks anteriores
    await db.execute("UPDATE picks SET is_active = 0")

    # 1. Pronóstico Gratuito Real de Hoy (LaLiga EA Sports)
    await db.execute("""
        INSERT INTO picks (match_title, competition, match_time, selection, odds, stake, analysis, status, is_vip_next, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDIENTE', 0, 1)
    """, (
        "Getafe CF vs RC Celta de Vigo",
        "LaLiga EA Sports",
        "Hoy a las 19:00 h",
        "Menos de 2.5 Goles",
        1.68,
        2.0,
        "Análisis Táctico de Rigor Defensivo:\n"
        "• El Getafe de José Bordalás en el Coliseum concede apenas 0.88 xG por encuentro, apostando a un planteamiento de pocas concesiones y presión física.\n"
        "• El Celta de Vigo fuera de Balaídos acusa dificultades históricas de pegada (promedia menos de 1 gol por salida).\n"
        "• En 4 de los últimos 5 duelos directos entre ambos se cumplió el Menos de 2.5 goles.\n"
        "• Probabilidad matemática calculada: 67% (+EV frente a cuota 1.68 en operadores oficiales)."
    ))

    # 2. Siguiente Pronóstico de Pago por 7.99€ (Apuesta del Día Siguiente / Mañana)
    await db.execute("""
        INSERT INTO picks (match_title, competition, match_time, selection, odds, stake, analysis, status, is_vip_next, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDIENTE', 1, 1)
    """, (
        "Internazionale vs Real Madrid",
        "UEFA Champions League",
        "Mañana a las 21:00 h",
        "Real Madrid gana o empata + Más de 1.5 Goles",
        1.82,
        2.5,
        "Análisis Confidencial Champions League (Día Siguiente):\n"
        "• El Real Madrid en competición europea promedia 2.3 goles esperados y una efectividad extrema en transiciones ofensivas.\n"
        "• El Inter en San Siro asume riesgos adelantando líneas defensivas, lo que deja espacios críticos a la espalda de sus carrileros.\n"
        "• Cuota combinada de alto valor estadístico (+EV 1.82 con 68% de probabilidad esperada)."
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

async def get_user(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {"user_id": user_id, "is_admin": 0, "has_paid_access": 0, "has_seen_free_pick": 0, "paid_count": 0, "consumed_free_victory": 0}

async def make_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def is_admin_user(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] == 1:
                return True
        # Si aún no hay ningún admin en todo el sistema, el primero que ejecute /admintg será asignado admin
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1") as cursor:
            admins_count = (await cursor.fetchone())[0]
            if admins_count == 0:
                await make_admin(user_id)
                return True
            return False

async def get_admin_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE is_admin = 1") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def get_all_users() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY joined_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def get_payment_url() -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = 'payment_url'") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else DEFAULT_PAYMENT_URL

async def set_payment_url(new_url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO settings (key, value) VALUES ('payment_url', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (new_url,))
        await db.commit()

# ── Gestión de Pronósticos y Reseteo ─────────────────────────────────────────

async def get_free_pick() -> dict:
    """Obtiene la única apuesta gratuita activa de hoy."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM picks WHERE is_vip_next = 0 AND is_active = 1 ORDER BY id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}

async def get_next_paid_pick() -> dict:
    """Obtiene el siguiente pronóstico exclusivo de pago (Apuesta de Mañana por 7.99€)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM picks WHERE is_vip_next = 1 AND is_active = 1 ORDER BY id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}

async def mark_free_pick_won() -> dict:
    """
    Marca la apuesta gratuita como ACERTADO (VERDE).
    REGLA: A todos los que vieron el pronóstico gratis y NO pagaron,
    se les marca consumed_free_victory = 1.
    Esto garantiza que no puedan recibir otro pronóstico gratis ni beneficiarse de fallos futuros:
    ya tuvieron su acierto gratis y si no pagan, quedan bloqueados para siempre.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id FROM picks WHERE is_vip_next = 0 AND is_active = 1 ORDER BY id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row:
                pick_id = row[0]
                await db.execute("UPDATE picks SET status = 'ACERTADO' WHERE id = ?", (pick_id,))
                
                # Bloquear permanentemente el acceso gratis a los que vieron el verde y no pagaron
                await db.execute("""
                    UPDATE users 
                    SET consumed_free_victory = 1 
                    WHERE has_seen_free_pick = 1 AND has_paid_access = 0
                """)
                await db.commit()

                async with db.execute("SELECT * FROM picks WHERE id = ?", (pick_id,)) as c2:
                    return dict(await c2.fetchone())
            return {}

async def mark_pick_lost_and_compensate_all() -> tuple[dict, int]:
    """
    Marca la apuesta como FALLADO (ROJO).
    REGLA ESTRICTA DE COMPENSACIÓN:
    Solo se resetea a:
    1. Los que pagaron recientemente (has_paid_access == 1 o paid_count > 0).
    2. Los nuevos que entraron y estaban en su primera prueba gratuita (consumed_free_victory == 0 AND has_seen_free_pick == 1).
    LOS QUE YA COGIERON UN GRATIS EN EL PASADO QUE SE ACERTÓ Y NO VOLVIERON A PAGAR (consumed_free_victory == 1)
    NO SE RESETEAN NUNCA.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        pick_dict = {}
        async with db.execute("SELECT id FROM picks WHERE is_vip_next = 0 AND is_active = 1 ORDER BY id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row:
                pick_id = row[0]
                await db.execute("UPDATE picks SET status = 'FALLADO' WHERE id = ?", (pick_id,))
                async with db.execute("SELECT * FROM picks WHERE id = ?", (pick_id,)) as c2:
                    pick_dict = dict(await c2.fetchone())

        # Resetear ÚNICAMENTE a los que pagaron O a nuevos en su primera prueba fallida
        cursor_users = await db.execute("""
            UPDATE users 
            SET has_seen_free_pick = 0, has_paid_access = 1 
            WHERE (has_paid_access = 1) 
               OR (consumed_free_victory = 0 AND has_seen_free_pick = 1)
        """)
        total_reset = cursor_users.rowcount
        await db.commit()
        return pick_dict, total_reset

async def mark_user_viewed_free_pick(user_id: int):
    """Marca que el usuario ya vio su pronóstico gratuito de prueba."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET has_seen_free_pick = 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def mark_user_viewed_paid_pick(user_id: int):
    """El usuario que pagó ve el pronóstico; consumió este ciclo pagado."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET has_seen_free_pick = 1, has_paid_access = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

async def set_new_free_pick(match_title: str, competition: str, match_time: str, selection: str, odds: float, stake: float, analysis: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE picks SET is_active = 0 WHERE is_vip_next = 0")
        await db.execute("""
            INSERT INTO picks (match_title, competition, match_time, selection, odds, stake, analysis, status, is_vip_next, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDIENTE', 0, 1)
        """, (match_title, competition, match_time, selection, odds, stake, analysis))
        await db.commit()

async def set_new_paid_pick(match_title: str, competition: str, match_time: str, selection: str, odds: float, stake: float, analysis: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE picks SET is_active = 0 WHERE is_vip_next = 1")
        await db.execute("""
            INSERT INTO picks (match_title, competition, match_time, selection, odds, stake, analysis, status, is_vip_next, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDIENTE', 1, 1)
        """, (match_title, competition, match_time, selection, odds, stake, analysis))
        await db.commit()

# ── Justificantes y Aprobación con Reseteo ───────────────────────────────────

async def add_receipt(user_id: int, username: str, photo_file_id: str, ai_analysis: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO receipts (user_id, username, photo_file_id, ai_analysis, status)
            VALUES (?, ?, ?, ?, 'PENDIENTE')
        """, (user_id, username, photo_file_id, ai_analysis))
        await db.commit()
        return cursor.lastrowid

async def get_pending_receipts() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM receipts WHERE status = 'PENDIENTE' ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def approve_receipt_and_reset_user(receipt_id: int) -> dict:
    """
    Aprueba el comprobante de pago de 7.99€ y RESETA EL BOT DEL USUARIO.
    Al resetearse, se le otorga acceso a la apuesta de mañana (has_paid_access = 1, has_seen_free_pick = 0).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("UPDATE receipts SET status = 'APROBADO' WHERE id = ?", (receipt_id,))
        async with db.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                r_dict = dict(row)
                target_uid = r_dict["user_id"]
                # RESETEAR EL BOT AL USUARIO: se le activa acceso pagado, se le borra el bloqueo
                await db.execute("""
                    UPDATE users 
                    SET has_paid_access = 1, 
                        has_seen_free_pick = 0, 
                        consumed_free_victory = 0,
                        paid_count = paid_count + 1 
                    WHERE user_id = ?
                """, (target_uid,))
                await db.commit()
                return r_dict
            return {}

async def reject_receipt(receipt_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("UPDATE receipts SET status = 'RECHAZADO' WHERE id = ?", (receipt_id,))
        async with db.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}

async def get_admin_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c1:
            total_users = (await c1.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE has_paid_access = 1") as c2:
            paid_users = (await c2.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM receipts WHERE status = 'PENDIENTE'") as c3:
            pending_receipts = (await c3.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM receipts WHERE status = 'APROBADO'") as c4:
            approved_receipts = (await c4.fetchone())[0]
        return {
            "total_users": total_users,
            "paid_users": paid_users,
            "pending_receipts": pending_receipts,
            "approved_receipts": approved_receipts
        }

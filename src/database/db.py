import aiosqlite
import os
import json
import calendar as cal
from datetime import datetime

# Baza fayli manzili
DB_PATH = "database.db"

# ADMIN USER ID - BU YERGA O'Z TELEGRAM ID INGIZNI KIRITING!
ADMIN_USER_ID = 5830567800  # <-- BU YERGA O'ZGARTIRING!

WEEKDAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]

async def init_db():
    """Bazani va jadvallarni yaratish"""
    async with aiosqlite.connect(DB_PATH) as conn:
        # Users jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT DEFAULT 'User',
                full_name TEXT DEFAULT '',
                username TEXT DEFAULT '',
                hourly_rate REAL DEFAULT 12500,
                tax_rate REAL DEFAULT 3.3,
                work_days TEXT DEFAULT '월,화,수,목,금,토,일',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Work_logs jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS work_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                work_date TEXT,
                hours REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, work_date) 
            )
        """)

        # workplace_id ustunini qo'shish (agar yo'q bo'lsa)
        try:
            await conn.execute("ALTER TABLE work_logs ADD COLUMN workplace_id INTEGER DEFAULT 1")
        except:
            pass  # Ustun allaqachon mavjud

        # weekly_schedule ustunini qo'shish (kun -> soat JSON, masalan {"월":10,"화":0,...})
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN weekly_schedule TEXT DEFAULT '{}'")
        except:
            pass  # Ustun allaqachon mavjud

        # Workplaces jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS workplaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Admin actions log (audit)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action_type TEXT,
                target_user_id INTEGER,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.commit()

def is_admin(user_id):
    """Foydalanuvchi admin ekanligini tekshirish"""
    return user_id == ADMIN_USER_ID

async def is_user_active(user_id):
    """Foydalanuvchi faol ekanligini tekshirish (bloklanmaganmi)"""
    # Admin har doim faol
    if is_admin(user_id):
        return True

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_active FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            if result:
                return result[0] == 1
            # Yangi user - faol hisoblanadi
            return True

async def get_user_full_info(user_id):
    """Foydalanuvchining barcha sozlamalarini olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT name, hourly_rate, tax_rate, work_days FROM users WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                # Yangi foydalanuvchi - bazaga qo'shish
                await db.execute(
                    "INSERT INTO users (user_id) VALUES (?)", 
                    (user_id,)
                )
                await db.commit()
                return "User", 12500, 3.3, "월,화,수,목,금,토,일"
            return row

async def update_user_info(user_id, full_name=None, username=None):
    """Foydalanuvchi ma'lumotlarini yangilash yoki yaratish"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Avval user borligini tekshiramiz
        async with db.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            exists = await cursor.fetchone()

        if exists:
            # Update qilamiz
            await db.execute(
                "UPDATE users SET full_name = ?, username = ? WHERE user_id = ?",
                (full_name or '', username or '', user_id)
            )
        else:
            # Insert qilamiz
            await db.execute(
                "INSERT INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
                (user_id, full_name or '', username or '')
            )
        await db.commit()

async def get_all_users():
    """Barcha foydalanuvchilar ro'yxati"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, name, full_name, username, is_active, created_at 
            FROM users 
            ORDER BY created_at DESC
        """) as cursor:
            return await cursor.fetchall()

async def get_user_stats(user_id, month=None):
    """Foydalanuvchining oylik statistikasi"""
    if month is None:
        month = datetime.now().strftime('%Y-%m')

    async with aiosqlite.connect(DB_PATH) as db:
        # Jami soatlar
        async with db.execute("""
            SELECT SUM(hours) FROM work_logs 
            WHERE user_id = ? AND work_date LIKE ?
        """, (user_id, f"{month}%")) as cursor:
            result = await cursor.fetchone()
            total_hours = result[0] if result[0] else 0

        # Sozlamalar
        async with db.execute("""
            SELECT hourly_rate, tax_rate FROM users WHERE user_id = ?
        """, (user_id,)) as cursor:
            settings = await cursor.fetchone()
            hourly_rate = settings[0] if settings else 12500
            tax_rate = settings[1] if settings else 3.3

        # Hisob-kitoblar
        gross_pay = total_hours * hourly_rate
        tax_amount = gross_pay * (tax_rate / 100)
        net_pay = gross_pay - tax_amount

        return {
            'total_hours': total_hours,
            'hourly_rate': hourly_rate,
            'tax_rate': tax_rate,
            'gross_pay': gross_pay,
            'tax_amount': tax_amount,
            'net_pay': net_pay
        }

async def log_admin_action(admin_id, action_type, target_user_id, description):
    """Admin amallarini log qilish"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO admin_actions (admin_id, action_type, target_user_id, description)
            VALUES (?, ?, ?, ?)
        """, (admin_id, action_type, target_user_id, description))
        await db.commit()

async def get_user_settings(user_id):
    """Faqat rate va tax olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT hourly_rate, tax_rate FROM users WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return 12500, 3.3
            return row

async def update_user_rate(user_id, new_rate):
    """Soatlik to'lovni yangilash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET hourly_rate = ? WHERE user_id = ?",
            (new_rate, user_id)
        )
        await db.commit()

async def update_user_tax(user_id, new_tax):
    """Soliq stavkasini yangilash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET tax_rate = ? WHERE user_id = ?",
            (new_tax, user_id)
        )
        await db.commit()

async def update_work_days(user_id, work_days_str):
    """Ish kunlarini yangilash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET work_days = ? WHERE user_id = ?",
            (work_days_str, user_id)
        )
        await db.commit()

async def add_workplace(user_id, name):
    """Yangi ishxona qo'shish"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO workplaces (user_id, name) VALUES (?, ?)",
            (user_id, name)
        )
        await db.commit()
        async with db.execute("SELECT last_insert_rowid()") as cursor:
            result = await cursor.fetchone()
            return result[0]

async def get_user_workplaces(user_id):
    """Foydalanuvchining barcha ishxonalari"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, name FROM workplaces WHERE user_id = ? ORDER BY id",
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()

async def get_workplace_name(workplace_id):
    """Ishxona nomini olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT name FROM workplaces WHERE id = ?",
            (workplace_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else "알 수 없음"

async def get_monthly_logs_by_workplace(user_id, workplace_id, year, month):
    """Ishxona bo'yicha oylik ma'lumotlar"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT work_date, hours FROM work_logs
            WHERE user_id = ? AND workplace_id = ?
            AND work_date LIKE ?
            ORDER BY work_date
        """, (user_id, workplace_id, f"{year}-{month:02d}%")) as cursor:
            return await cursor.fetchall()

async def save_work_log_with_workplace(user_id, workplace_id, work_date, hours):
    """Ishxona bilan birga log saqlash"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Avval mavjud yozuvni o'chirish (agar boshqa workplace_id bo'lsa)
        await db.execute("""
            DELETE FROM work_logs 
            WHERE user_id = ? AND work_date = ? AND workplace_id != ?
        """, (user_id, work_date, workplace_id))

        # Keyin yangi yoki yangilangan yozuvni qo'shish
        await db.execute("""
            INSERT INTO work_logs (user_id, workplace_id, work_date, hours)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, work_date) DO UPDATE SET 
                workplace_id = excluded.workplace_id,
                hours = excluded.hours
        """, (user_id, workplace_id, work_date, hours))
        await db.commit()

async def delete_workplace(workplace_id):
    """Ishxonani o'chirish (ishxona va unga tegishli barcha loglar)"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Avval ishxonaga tegishli barcha work_logs ni o'chirish
        await db.execute(
            "DELETE FROM work_logs WHERE workplace_id = ?",
            (workplace_id,)
        )
        # Keyin ishxonani o'chirish
        await db.execute(
            "DELETE FROM workplaces WHERE id = ?",
            (workplace_id,)
        )
        await db.commit()

# ===================== YANGI: HAFTALIK JADVAL (KUN + SOAT) =====================

async def get_user_schedule(user_id):
    """Foydalanuvchining haftalik jadvalini olish: {"월": 10, "화": 0, ...}"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT weekly_schedule FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or not row[0]:
                return {}
            try:
                return json.loads(row[0])
            except Exception:
                return {}

async def save_user_schedule(user_id, schedule: dict):
    """Haftalik jadvalni saqlash (JSON) va work_days ustunini ham yangilash"""
    work_days = ','.join([d for d in WEEKDAY_NAMES if schedule.get(d, 0) > 0])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            exists = await cursor.fetchone()
        if not exists:
            await db.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        await db.execute(
            "UPDATE users SET weekly_schedule = ?, work_days = ? WHERE user_id = ?",
            (json.dumps(schedule, ensure_ascii=False), work_days, user_id)
        )
        await db.commit()

async def fill_month_from_schedule(user_id, workplace_id, schedule: dict, year=None, month=None):
    """Haftalik jadval asosida butun oyni oldindan to'ldirish"""
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    days_in_month = cal.monthrange(year, month)[1]

    async with aiosqlite.connect(DB_PATH) as db:
        for day in range(1, days_in_month + 1):
            date_obj = datetime(year, month, day)
            day_name = WEEKDAY_NAMES[date_obj.weekday()]
            hours = schedule.get(day_name, 0)
            work_date = date_obj.strftime("%Y-%m-%d")

            await db.execute("""
                INSERT INTO work_logs (user_id, workplace_id, work_date, hours)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, work_date) DO UPDATE SET 
                    workplace_id = excluded.workplace_id,
                    hours = excluded.hours
            """, (user_id, workplace_id, work_date, hours))
        await db.commit()

async def get_log_hours(user_id, workplace_id, work_date):
    """Aynan bir kun uchun soatni olish (mavjud bo'lmasa None qaytaradi)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT hours FROM work_logs WHERE user_id = ? AND workplace_id = ? AND work_date = ?",
            (user_id, workplace_id, work_date)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_all_monthly_summaries(user_id, workplace_id):
    """Berilgan ishxona bo'yicha barcha oylarning umumiy statistikasi (eng yangisidan eskisiga)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT substr(work_date, 1, 7) as ym,
                   SUM(CASE WHEN hours > 0 THEN hours ELSE 0 END) as total_hours,
                   SUM(CASE WHEN hours > 0 THEN 1 ELSE 0 END) as work_days_count
            FROM work_logs
            WHERE user_id = ? AND workplace_id = ?
            GROUP BY ym
            ORDER BY ym DESC
        """, (user_id, workplace_id)) as cursor:
            return await cursor.fetchall()
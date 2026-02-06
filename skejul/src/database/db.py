import aiosqlite
import os

# Baza fayli manzili
DB_PATH = "database.db"

# ADMIN USER ID - BU YERGA O'Z TELEGRAM ID INGIZNI KIRITING!
ADMIN_USER_ID = 5830567800  # <-- BU YERGA O'ZGARTIRING!

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
        from datetime import datetime
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
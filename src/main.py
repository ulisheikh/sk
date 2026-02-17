import pytz
import asyncio
import sys
import aiosqlite
from pathlib import Path
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

# Loyiha yo'lini sozlash
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils.config import BOT_TOKEN
from src.handlers import hd
from src.handlers import hd_admin
from src.handlers import hd_workplace
from src.database import db
import src.keyboards.kbd as kbd
from aiogram.types import BotCommand

async def set_bot_commands(bot: Bot):
    """Chap menyu commandalar"""
    commands = [
        BotCommand(command="start", description="🏠 메인 메뉴"),
        BotCommand(command="info", description="ℹ️ 내 정보")
    ]
    await bot.set_my_commands(commands)

async def send_morning_reminder(bot: Bot):
    """Har kuni 05:00 da (Seoul vaqti bilan) inline tugmalar bilan so'rov yuborish"""
    try:
        # Koreya vaqt mintaqasini belgilaymiz (Server Parijda bo'lsa ham adashmasligi uchun)
        seoul_tz = pytz.timezone("Asia/Seoul")
        
        # Ma'lumotlar bazasidan foydalanuvchilarni olish
        async with aiosqlite.connect(db.DB_PATH) as conn:
            async with conn.execute("SELECT user_id FROM users") as cursor:
                users = await cursor.fetchall()
        
        # Bugungi sana (Aynan Koreya vaqti bilan)
        today = datetime.now(seoul_tz)
        
        # Kecha sanasi (Koreya vaqtidan 1 kun ayiramiz)
        yesterday = today - timedelta(days=1)
        yesterday_str = f"{yesterday.month}월 {yesterday.day}일"
        
        # DEBUG - terminalda ko'rish uchun (Koreya vaqtini ko'rsatadi)
        print(f"[REMINDER] Xabar yuborish vaqti (Seoul): {today.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[REMINDER] So'ralayotgan kun: {yesterday_str} ({yesterday.strftime('%Y-%m-%d')})")
        print(f"[REMINDER] Foydalanuvchilar soni: {len(users)}")
        
        for user in users:
            try:
                # user[0] bu user_id
                await bot.send_message(
                    user[0], 
                    f"☀️ 좋은 아침입니다!\n\n어제 ({yesterday_str}) 근무 시간을 기록해주세요:",
                    reply_markup=kbd.daily_report_inline()
                )
                print(f"[REMINDER] Xabar yuborildi: user_id={user[0]}")
            except Exception as e:
                print(f"[ERROR] Foydalanuvchiga yuborib bo'lmadi user_id={user[0]}: {e}")
                continue
                
        print(f"[REMINDER] Barcha xabarlar yuborildi!")
        
    except Exception as e:
        print(f"[ERROR] Eslatma yuborishda xato: {e}")

async def main():
    # Ma'lumotlar bazasini ishga tushirish
    await db.init_db()
    
    # Botni sozlash
    bot = Bot(token=BOT_TOKEN)
    
    # Chap menu commandalar
    await set_bot_commands(bot)
    
    dp = Dispatcher()
    dp.include_router(hd_admin.admin_router)  # Admin router birinchi
    dp.include_router(hd_workplace.router)  # Yangi workplace router
    dp.include_router(hd.router)  # Eski router (fallback)

    # Scheduler (Koreya vaqti bilan 05:00)
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
    scheduler.add_job(send_morning_reminder, "cron", hour=5, minute=0, args=[bot])
    scheduler.start()

    print("=" * 50)
    print("🤖 봇이 시작되었습니다 (Korea Time Zone)")
    print("=" * 50)
    print(f"📅 현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏰ 알림 시간: 매일 오전 5시")
    print(f"🔔 다음 알림: {scheduler.get_jobs()[0].next_run_time}")
    print("=" * 50)
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n[STOP] Bot to'xtatildi")



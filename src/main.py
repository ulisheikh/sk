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
from src.database import db
import src.keyboards.kbd as kbd

async def send_morning_reminder(bot: Bot):
    """Har kuni 05:00 da inline tugmalar bilan so'rov yuborish"""
    try:
        async with aiosqlite.connect(db.DB_PATH) as conn:
            async with conn.execute("SELECT user_id FROM users") as cursor:
                users = await cursor.fetchall()
        
        # Kecha sanasini aniqlash
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_str = f"{yesterday.month}월 {yesterday.day}일"
        
        for user in users:
            try:
                await bot.send_message(
                    user[0], 
                    f"☀️ 좋은 아침입니다!\n\n어제 ({yesterday_str}) 근무 시간을 기록해주세요:",
                    reply_markup=kbd.daily_report_inline()
                )
            except Exception:
                continue
    except Exception as e:
        print(f"Eslatma yuborishda xato: {e}")

async def main():
    # Ma'lumotlar bazasini ishga tushirish
    await db.init_db()
    
    # Botni sozlash
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(hd_admin.admin_router)  # Admin router birinchi
    dp.include_router(hd.router)  # Keyin oddiy router

    # Scheduler (Koreya vaqti bilan 05:00)
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
    scheduler.add_job(send_morning_reminder, "cron", hour=5, minute=0, args=[bot])
    scheduler.start()

    print("--- 봇이 시작되었습니다 (Korea Time Zone) ---")
    print(f"현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("매일 오전 5시에 근무 시간 기록 알림이 전송됩니다.")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot to'xtatildi")
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

from config import BOT_TOKEN
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
        BotCommand(command="info", description="👤 프로필"),
        BotCommand(command="monthly", description="📅 월별 전체 보기")
    ]
    await bot.set_my_commands(commands)

async def send_morning_reminder(bot: Bot):
    """Har kuni 05:00 da (Seoul vaqti bilan) - agar oldindan jadval bo'yicha ma'lumot
    to'ldirilgan bo'lsa, faqat tasdiqlashni so'raydi. Aks holda eskisidek soat so'raydi."""
    try:
        seoul_tz = pytz.timezone("Asia/Seoul")

        async with aiosqlite.connect(db.DB_PATH) as conn:
            async with conn.execute("SELECT user_id FROM users") as cursor:
                users = await cursor.fetchall()

        today = datetime.now(seoul_tz)
        yesterday = today - timedelta(days=1)
        yesterday_str = f"{yesterday.month}월 {yesterday.day}일"
        yesterday_date = yesterday.strftime("%Y-%m-%d")

        print(f"[REMINDER] Xabar yuborish vaqti (Seoul): {today.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[REMINDER] So'ralayotgan kun: {yesterday_str} ({yesterday_date})")
        print(f"[REMINDER] Foydalanuvchilar soni: {len(users)}")

        for user in users:
            user_id = user[0]
            try:
                workplaces = await db.get_user_workplaces(user_id)

                if not workplaces:
                    # Ishxona yo'q bo'lsa - eski usulda so'ramaymiz, o'tkazib yuboramiz
                    continue

                workplace_id = workplaces[0][0]

                # Jadval bo'yicha oldindan to'ldirilgan ma'lumot bormi tekshirish
                existing_hours = await db.get_log_hours(user_id, workplace_id, yesterday_date)

                if existing_hours is not None:
                    # Ma'lumot allaqachon mavjud - faqat tasdiqlashni so'raymiz
                    if existing_hours == 0:
                        status_text = "🏖 휴무로 등록되어 있습니다"
                    else:
                        status_text = f"{existing_hours}시간 근무로 등록되어 있습니다"

                    text = (
                        f"☀️ 좋은 아침입니다!\n\n"
                        f"어제 ({yesterday_str}) 근무표에 따르면 {status_text}.\n\n"
                        f"맞습니까?"
                    )
                    await bot.send_message(
                        user_id,
                        text,
                        reply_markup=kbd.daily_confirm_inline(workplace_id, yesterday_date)
                    )
                else:
                    # Ma'lumot yo'q - eski usulda so'raymiz
                    await bot.send_message(
                        user_id,
                        f"☀️ 좋은 아침입니다!\n\n어제 ({yesterday_str}) 근무 시간을 기록해주세요:",
                        reply_markup=kbd.daily_report_inline()
                    )

                print(f"[REMINDER] Xabar yuborildi: user_id={user_id}")
            except Exception as e:
                print(f"[ERROR] Foydalanuvchiga yuborib bo'lmadi user_id={user_id}: {e}")
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
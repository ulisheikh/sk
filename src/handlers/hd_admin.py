from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
import calendar
from datetime import datetime
from src.database import db
from src.keyboards import kbd, kbd_admin

admin_router = Router()

class AdminForm(StatesGroup):
    admin_edit_rate = State()
    admin_edit_tax = State()
    admin_manual_hours = State()

# Hafta kunini olish
def get_weekday_korean(date_obj):
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    return weekdays[date_obj.weekday()]

# --- MAXFIY ADMIN KOMANDA ---
@admin_router.message(F.text == "/my_users")
async def admin_panel(message: Message):
    """Maxfiy admin panel - faqat admin ko'radi"""
    if not db.is_admin(message.from_user.id):
        # Oddiy foydalanuvchi uchun xech narsa ko'rsatilmaydi
        return
    
    await message.answer(
        "🔐 관리자 패널\n\n선택하세요:",
        reply_markup=kbd_admin.admin_main_menu()
    )

@admin_router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    """Admin panelga qaytish"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    await callback.message.edit_text(
        "🔐 관리자 패널\n\n선택하세요:",
        reply_markup=kbd_admin.admin_main_menu()
    )

# --- FOYDALANUVCHILAR RO'YXATI ---
@admin_router.callback_query(F.data == "admin_users")
async def show_users_list(callback: CallbackQuery):
    """Barcha foydalanuvchilar ro'yxati"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    users = await db.get_all_users()
    
    if not users:
        await callback.message.edit_text(
            "📋 등록된 사용자가 없습니다.",
            reply_markup=kbd_admin.admin_main_menu()
        )
        return
    
    text = f"👥 사용자 목록 ({len(users)}명)\n\n사용자를 선택하세요:"
    
    await callback.message.edit_text(
        text,
        reply_markup=kbd_admin.admin_users_list(users)
    )

# --- TANLANGAN FOYDALANUVCHI ---
@admin_router.callback_query(F.data.startswith("admin_user_"))
async def show_user_menu(callback: CallbackQuery):
    """Foydalanuvchi menyusi"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    # Foydalanuvchi ma'lumotlari
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute(
            "SELECT full_name, username, hourly_rate, tax_rate, work_days FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            user_data = await cursor.fetchone()
    
    if not user_data:
        await callback.answer("❌ 사용자를 찾을 수 없습니다.")
        return
    
    full_name, username, hourly_rate, tax_rate, work_days = user_data
    display_name = full_name if full_name else (username if username else f"User {user_id}")
    
    text = f"""👤 {display_name}

🔢 ID: {user_id}
🆔 사용자명: @{username if username else '없음'}

⚙️ 설정
💰 시급: {hourly_rate:,}원
📉 세금: {tax_rate}%
📅 근무요일: {work_days}

원하는 작업을 선택하세요:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=kbd_admin.admin_user_menu(user_id)
    )
    
    # Admin action log
    await db.log_admin_action(
        callback.from_user.id,
        "view_user",
        user_id,
        f"Viewed user profile"
    )

# --- FOYDALANUVCHI HISOBOTINI KO'RISH ---
@admin_router.callback_query(F.data.startswith("admin_view_"))
async def admin_view_report(callback: CallbackQuery):
    """Admin foydalanuvchining hisobotini ko'radi"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    user_id = int(callback.data.split("_")[-1])
    now = datetime.now()
    current_month = now.strftime('%Y-%m')

    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute("""
            SELECT work_date, hours FROM work_logs 
            WHERE user_id = ? AND work_date LIKE ?
            ORDER BY work_date ASC
        """, (user_id, f"{current_month}%")) as c:
            rows = await c.fetchall()
        
        async with conn.execute("""
            SELECT hourly_rate, tax_rate, full_name FROM users WHERE user_id = ?
        """, (user_id,)) as c:
            settings = await c.fetchone()
            hourly_rate = settings[0] if settings else 12500
            tax_rate = settings[1] if settings else 3.3
            full_name = settings[2] if settings and settings[2] else f"User {user_id}"

    if not rows:
        text = f"👤 {full_name}\n📅 {now.month}월 근무 기록이 없습니다."
    else:
        report_lines = [f"👤 {full_name}\n📅 {now.month}월 근무 상세 기록\n"]
        total_month_hours = 0
        
        for date_str, hours in rows:
            day_only = date_str.split('-')[-1]
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            weekday = get_weekday_korean(date_obj)
            
            if hours == 0:
                report_lines.append(f"▫️ {day_only}일 ({weekday}): 🏖 휴무")
            else:
                report_lines.append(f"▫️ {day_only}일 ({weekday}): {hours}시간")
                total_month_hours += hours
        
        gross_pay = total_month_hours * hourly_rate
        tax_amount = gross_pay * (tax_rate / 100)
        net_pay = gross_pay - tax_amount
        
        report_lines.append(f"\n━━━━━━━━━━━━━━")
        report_lines.append(f"⏱ 총 근무시간: {total_month_hours}시간")
        report_lines.append(f"💰 세전 급여: {gross_pay:,.0f}원")
        report_lines.append(f"📉 세금 ({tax_rate}%): {tax_amount:,.0f}원")
        report_lines.append(f"💵 실수령액: {net_pay:,.0f}원")

        text = "\n".join(report_lines)

    await callback.message.edit_text(
        text,
        reply_markup=kbd_admin.admin_user_menu(user_id),
        parse_mode=None
    )

# --- FOYDALANUVCHI KUNDALIGINI TAHRIRLASH ---
@admin_router.callback_query(F.data.startswith("admin_edit_"))
async def admin_edit_calendar(callback: CallbackQuery):
    """Admin foydalanuvchi uchun kalendar ko'rsatadi"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    user_id = int(callback.data.split("_")[-1])
    now = datetime.now()
    
    # User name
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute(
            "SELECT full_name, username FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            user_data = await cursor.fetchone()
    
    full_name = user_data[0] if user_data and user_data[0] else (user_data[1] if user_data and user_data[1] else f"User {user_id}")
    
    # Get worked days for current month
    current_month = now.strftime('%Y-%m')
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute(
            "SELECT work_date, hours FROM work_logs WHERE user_id = ? AND work_date LIKE ?",
            (user_id, f"{current_month}%")
        ) as cursor:
            work_data = await cursor.fetchall()
    
    # Create calendar with work indicators
    calendar_markup = await create_admin_calendar_with_work(user_id, work_data, now)
    
    await callback.message.edit_text(
        f"👤 {full_name}\n📅 {now.year}년 {now.month}월\n\n수정할 날짜를 선택하세요:\n\n• = 근무 기록됨 | 🏖 = 휴무",
        reply_markup=calendar_markup,
        parse_mode=None
    )

async def create_admin_calendar_with_work(user_id, work_data, now):
    """Ishlangan kunlar bilan kalendar yaratish"""
    import calendar
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    year = now.year
    month = now.month
    
    # Ishlangan kunlarni dict ga olish
    worked_days = {}
    for date_str, hours in work_data:
        day = int(date_str.split('-')[-1])
        worked_days[day] = hours
    
    # Hafta kunlari sarlavhasi
    weekday_headers = ["월", "화", "수", "목", "금", "토", "일"]
    for header in weekday_headers:
        builder.button(text=header, callback_data="ignore")
    builder.adjust(7)
    
    # Oyning birinchi kuni
    first_day = datetime(year, month, 1)
    weekday = first_day.weekday()
    
    # Oyning kunlar soni
    days_in_month = calendar.monthrange(year, month)[1]
    
    # Bo'sh joylar
    buttons = []
    for _ in range(weekday):
        buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
    
    # Kunlarni qo'shish
    current_day = now.day
    for day in range(1, days_in_month + 1):
        if day == current_day:
            text = f"📍{day}"
        elif day < current_day and day in worked_days:
            # Ishlangan yoki dam olgan
            if worked_days[day] == 0:
                text = f"🏖{day}"  # Dam olgan
            else:
                text = f"•{day}"   # Ishlagan
        elif day < current_day:
            # Hech narsa yozilmagan
            text = str(day)
        else:
            text = str(day)
        
        buttons.append(InlineKeyboardButton(
            text=text, 
            callback_data=f"admin_day_{user_id}_{day}"
        ))
    
    # 7 tadan guruplash
    for i in range(0, len(buttons), 7):
        builder.row(*buttons[i:i+7])
    
    # Orqaga
    builder.row(InlineKeyboardButton(text="⬅️ 뒤로", callback_data=f"admin_user_{user_id}"))
    
    return builder.as_markup()

@admin_router.callback_query(F.data.startswith("admin_day_"))
async def admin_select_day(callback: CallbackQuery):
    """Admin kun tanlaganda soatlarni ko'rsatish"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    parts = callback.data.split("_")
    user_id = int(parts[2])
    day = parts[3]
    
    now = datetime.now()
    selected_date = datetime(now.year, now.month, int(day))
    weekday = get_weekday_korean(selected_date)
    
    await callback.message.edit_text(
        f"📍 {now.month}월 {day}일 ({weekday})\n근무 시간을 선택하세요:",
        reply_markup=kbd_admin.admin_hours_inline(user_id, day)
    )

@admin_router.callback_query(F.data.startswith("admin_save_"))
async def admin_save_hours(callback: CallbackQuery):
    """Admin foydalanuvchi uchun soatlarni saqlaydi"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    parts = callback.data.split("_")
    user_id = int(parts[2])
    day = parts[3]
    hours = float(parts[4])
    
    work_date = datetime.now().strftime(f"%Y-%m-{int(day):02d}")

    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute("""
            INSERT INTO work_logs (user_id, work_date, hours) 
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, work_date) DO UPDATE SET hours = excluded.hours
        """, (user_id, work_date, hours))
        await conn.commit()

    # Log admin action
    await db.log_admin_action(
        callback.from_user.id,
        "edit_hours",
        user_id,
        f"Set {day}일 to {hours} hours"
    )

    if hours == 0:
        await callback.answer(f"✅ {day}일 휴무로 저장되었습니다!")
    else:
        await callback.answer(f"✅ {day}일 {hours}시간 저장완료!")
    
    await callback.message.edit_text(
        "다른 날짜를 선택하세요:",
        reply_markup=kbd_admin.admin_calendar_inline(user_id)
    )

# --- ADMIN SOZLAMALARNI O'ZGARTIRISH ---
@admin_router.callback_query(F.data.startswith("admin_settings_"))
async def admin_settings(callback: CallbackQuery):
    """Foydalanuvchi sozlamalarini o'zgartirish menyusi"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    await callback.message.edit_text(
        "⚙️ 설정 변경\n\n변경할 항목을 선택하세요:",
        reply_markup=kbd_admin.admin_settings_menu(user_id)
    )

@admin_router.callback_query(F.data.startswith("admin_rate_"))
async def admin_edit_rate(callback: CallbackQuery, state: FSMContext):
    """Admin soatlik to'lovni o'zgartiradi"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(target_user_id=user_id)
    
    await callback.message.answer("💰 새로운 시급을 입력하세요 (예: 12500):")
    await state.set_state(AdminForm.admin_edit_rate)

@admin_router.message(AdminForm.admin_edit_rate)
async def process_admin_rate(message: Message, state: FSMContext):
    if not db.is_admin(message.from_user.id):
        return
    
    try:
        new_rate = float(message.text.replace(',', '').replace('원', '').strip())
        data = await state.get_data()
        user_id = data['target_user_id']
        
        await db.update_user_rate(user_id, new_rate)
        
        # Log
        await db.log_admin_action(
            message.from_user.id,
            "change_rate",
            user_id,
            f"Changed hourly rate to {new_rate}"
        )
        
        await message.answer(
            f"✅ 시급이 {new_rate:,}원으로 변경되었습니다!",
            reply_markup=kbd_admin.admin_user_menu(user_id)
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ 올바른 숫자를 입력해주세요.")

# --- ADMIN SOLIQ O'ZGARTIRISH ---
@admin_router.callback_query(F.data.startswith("admin_tax_"))
async def admin_edit_tax(callback: CallbackQuery, state: FSMContext):
    """Admin soliq stavkasini o'zgartiradi"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(target_user_id=user_id)
    
    await callback.message.answer("📉 새로운 세금율을 입력하세요 (예: 3.3):")
    await state.set_state(AdminForm.admin_edit_tax)

@admin_router.message(AdminForm.admin_edit_tax)
async def process_admin_tax(message: Message, state: FSMContext):
    if not db.is_admin(message.from_user.id):
        return
    
    try:
        new_tax = float(message.text.replace(',', '.').replace('%', '').strip())
        data = await state.get_data()
        user_id = data['target_user_id']
        
        await db.update_user_tax(user_id, new_tax)
        
        # Log
        await db.log_admin_action(
            message.from_user.id,
            "change_tax",
            user_id,
            f"Changed tax rate to {new_tax}%"
        )
        
        await message.answer(
            f"✅ 세금율이 {new_tax}%로 변경되었습니다!",
            reply_markup=kbd_admin.admin_user_menu(user_id)
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ 올바른 숫자를 입력해주세요.")

# --- ADMIN ISH KUNLARI O'ZGARTIRISH ---
@admin_router.callback_query(F.data.startswith("admin_workdays_"))
async def admin_edit_workdays(callback: CallbackQuery):
    """Admin ish kunlarini o'zgartiradi"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    # Hozirgi sozlamalarni olish
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute(
            "SELECT work_days FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            current_days = result[0] if result else "월,화,수,목,금,토,일"
    
    selected_days = current_days.split(',')
    
    await callback.message.edit_text(
        f"📅 근무요일 설정\n\n현재: {current_days}\n\n요일을 선택하세요:",
        reply_markup=kbd_admin.admin_workdays_inline(user_id, selected_days),
        parse_mode=None
    )

@admin_router.callback_query(F.data.startswith("admin_toggle_"))
async def admin_toggle_workday(callback: CallbackQuery):
    """Admin ish kunini on/off qiladi"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    parts = callback.data.split("_")
    user_id = int(parts[2])
    day = parts[3]
    
    # Hozirgi sozlamalarni olish
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute(
            "SELECT work_days FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            current_days = result[0] if result else "월,화,수,목,금,토,일"
    
    selected_days = current_days.split(',')
    
    # Toggle
    if day in selected_days:
        selected_days.remove(day)
    else:
        selected_days.append(day)
    
    await callback.message.edit_text(
        f"📅 근무요일 설정\n\n선택된 요일: {','.join(selected_days)}\n\n요일을 선택하세요:",
        reply_markup=kbd_admin.admin_workdays_inline(user_id, selected_days),
        parse_mode=None
    )

@admin_router.callback_query(F.data.startswith("admin_save_workdays_"))
async def admin_save_workdays(callback: CallbackQuery):
    """Admin ish kunlarini saqlaydi"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    # Hozirgi sozlamalarni olish va saqlash
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute(
            "SELECT work_days FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            work_days = result[0] if result else "월,화,수,목,금,토,일"
    
    # Log
    await db.log_admin_action(
        callback.from_user.id,
        "change_workdays",
        user_id,
        f"Changed work days to {work_days}"
    )
    
    await callback.answer("✅ 근무요일이 저장되었습니다!")
    
    # User menyusiga qaytish
    await show_user_menu(callback)

# --- UMUMIY STATISTIKA ---
@admin_router.callback_query(F.data == "admin_stats")
async def show_all_stats(callback: CallbackQuery):
    """Barcha foydalanuvchilarning statistikasi"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    now = datetime.now()
    current_month = now.strftime('%Y-%m')
    
    users = await db.get_all_users()
    
    if not users:
        await callback.message.edit_text(
            "📊 통계가 없습니다.",
            reply_markup=kbd_admin.admin_main_menu()
        )
        return
    
    report_lines = [f"📊 전체 통계 ({now.month}월)\n"]
    total_all_hours = 0
    total_all_pay = 0
    
    for user in users:
        user_id = user[0]
        full_name = user[2] if user[2] else (user[3] if user[3] else f"User {user_id}")
        
        stats = await db.get_user_stats(user_id, current_month)
        
        report_lines.append(f"\n👤 {full_name}")
        report_lines.append(f"   ⏱ {stats['total_hours']}시간")
        report_lines.append(f"   💵 {stats['net_pay']:,.0f}원")
        
        total_all_hours += stats['total_hours']
        total_all_pay += stats['net_pay']
    
    report_lines.append(f"\n━━━━━━━━━━━━━━")
    report_lines.append(f"⏱ 총 근무시간: {total_all_hours}시간")
    report_lines.append(f"💰 총 지급액: {total_all_pay:,.0f}원")
    
    text = "\n".join(report_lines)
    
    await callback.message.edit_text(
        text,
        reply_markup=kbd_admin.admin_main_menu(),
        parse_mode=None
    )

# --- FOYDALANUVCHINI BLOKLASH ---
@admin_router.callback_query(F.data.startswith("admin_block_"))
async def admin_block_user(callback: CallbackQuery):
    """Foydalanuvchini bloklash (tasdiqlash bilan)"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    # Foydalanuvchi ma'lumotlari
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute(
            "SELECT full_name, username, is_active FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            user_data = await cursor.fetchone()
    
    if not user_data:
        await callback.answer("❌ 사용자를 찾을 수 없습니다.")
        return
    
    full_name, username, is_active = user_data
    display_name = full_name if full_name else (username if username else f"User {user_id}")
    
    # Tasdiqlash
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    if is_active:
        # Bloklash
        builder.row(
            InlineKeyboardButton(text="✅ 차단 확인", callback_data=f"confirm_block_{user_id}"),
            InlineKeyboardButton(text="❌ 취소", callback_data=f"admin_user_{user_id}")
        )
        text = f"🚫 사용자 차단\n\n👤 {display_name}\n\n정말로 이 사용자를 차단하시겠습니까?\n차단된 사용자는 봇을 사용할 수 없습니다."
    else:
        # Blokdan chiqarish
        builder.row(
            InlineKeyboardButton(text="✅ 차단 해제 확인", callback_data=f"confirm_unblock_{user_id}"),
            InlineKeyboardButton(text="❌ 취소", callback_data=f"admin_user_{user_id}")
        )
        text = f"✅ 차단 해제\n\n👤 {display_name}\n\n이 사용자의 차단을 해제하시겠습니까?"
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode=None
    )

@admin_router.callback_query(F.data.startswith("confirm_block_"))
async def confirm_block_user(callback: CallbackQuery):
    """Bloklashni tasdiqlash"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute(
            "UPDATE users SET is_active = 0 WHERE user_id = ?",
            (user_id,)
        )
        await conn.commit()
    
    # Log
    await db.log_admin_action(
        callback.from_user.id,
        "block_user",
        user_id,
        "User blocked"
    )
    
    await callback.answer("✅ 사용자가 차단되었습니다.")
    
    # User menyusiga qaytish
    await show_user_menu(callback)

@admin_router.callback_query(F.data.startswith("confirm_unblock_"))
async def confirm_unblock_user(callback: CallbackQuery):
    """Blokdan chiqarishni tasdiqlash"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute(
            "UPDATE users SET is_active = 1 WHERE user_id = ?",
            (user_id,)
        )
        await conn.commit()
    
    # Log
    await db.log_admin_action(
        callback.from_user.id,
        "unblock_user",
        user_id,
        "User unblocked"
    )
    
    await callback.answer("✅ 차단이 해제되었습니다.")
    
    # User menyusiga qaytish
    await show_user_menu(callback)

# --- FOYDALANUVCHINI O'CHIRISH ---
@admin_router.callback_query(F.data.startswith("admin_delete_"))
async def admin_delete_user(callback: CallbackQuery):
    """Foydalanuvchini o'chirish (tasdiqlash bilan)"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    # Foydalanuvchi ma'lumotlari
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute(
            "SELECT full_name, username FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            user_data = await cursor.fetchone()
    
    if not user_data:
        await callback.answer("❌ 사용자를 찾을 수 없습니다.")
        return
    
    full_name, username = user_data
    display_name = full_name if full_name else (username if username else f"User {user_id}")
    
    # Tasdiqlash
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ 삭제 확인", callback_data=f"confirm_delete_{user_id}"),
        InlineKeyboardButton(text="❌ 취소", callback_data=f"admin_user_{user_id}")
    )
    
    await callback.message.edit_text(
        f"🗑 사용자 삭제\n\n👤 {display_name}\n\n⚠️ 경고: 이 작업은 되돌릴 수 없습니다!\n\n정말로 이 사용자와 모든 근무 기록을 삭제하시겠습니까?",
        reply_markup=builder.as_markup(),
        parse_mode=None
    )

@admin_router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_user(callback: CallbackQuery):
    """O'chirishni tasdiqlash - backup bilan"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ 권한이 없습니다.")
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    # BACKUP YARATISH
    import os
    import json
    from datetime import datetime
    
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # User ma'lumotlarini olish
    async with aiosqlite.connect(db.DB_PATH) as conn:
        # User info
        async with conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            user_data = await cursor.fetchone()
            columns = [description[0] for description in cursor.description]
            user_dict = dict(zip(columns, user_data)) if user_data else {}
        
        # Work logs
        async with conn.execute(
            "SELECT * FROM work_logs WHERE user_id = ?", (user_id,)
        ) as cursor:
            work_logs = await cursor.fetchall()
            work_columns = [description[0] for description in cursor.description]
            work_list = [dict(zip(work_columns, row)) for row in work_logs]
    
    # Backup faylga yozish
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/user_{user_id}_{timestamp}.json"
    
    backup_data = {
        "user_info": user_dict,
        "work_logs": work_list,
        "deleted_at": timestamp,
        "deleted_by": callback.from_user.id
    }
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
    
    # DATABASE dan o'chirish
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute("DELETE FROM work_logs WHERE user_id = ?", (user_id,))
        await conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await conn.commit()
    
    # Log
    await db.log_admin_action(
        callback.from_user.id,
        "delete_user",
        user_id,
        f"User deleted and backed up to {backup_file}"
    )
    
    await callback.answer(f"✅ 사용자가 삭제되었습니다.\n백업: {backup_file}")
    
    # Foydalanuvchilar ro'yxatiga qaytish
    await show_users_list(callback)
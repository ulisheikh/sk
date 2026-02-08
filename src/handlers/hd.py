from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
import calendar
from datetime import datetime, timedelta
from src.database import db
from src.keyboards import kbd

router = Router()

class Form(StatesGroup):
    edit_manual_day = State()
    edit_rate = State()
    edit_tax = State()
    daily_manual_input = State()
    edit_manual_workplace_day = State()

# ===== HELPER FUNKSIYA - XATOLARNI OLDINI OLISH =====
async def safe_edit_or_answer(callback, text, reply_markup=None, parse_mode=None):
    """Xabarni tahrirlash yoki yangi yuborish (rasm xatoligini oldini oladi)"""
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except:
        # Agar xabar rasm bo'lsa yoki boshqa xato bo'lsa
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

# Hafta kunlarini olish funksiyasi
def get_weekday_korean(date_obj):
    """Berilgan sananing hafta kunini koreys tilida qaytaradi"""
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    return weekdays[date_obj.weekday()]

# --- START VA ASOSIY MENYU ---
@router.message(F.text == "/start")
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    # Foydalanuvchi ma'lumotlarini yangilash yoki yaratish
    await db.update_user_info(
        user_id,
        message.from_user.full_name,
        message.from_user.username
    )
    
    # Bloklangan userlarni tekshirish
    if not await db.is_user_active(user_id):
        await message.answer(
            "🚫 차단된 사용자입니다.\n관리자에게 문의하세요.",
            parse_mode=None
        )
        return
    
    await message.answer(
        "원하시는 메뉴를 선택해주세요:", 
        reply_markup=kbd.main_menu_inline(),
        parse_mode=None
    )

@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await safe_edit_or_answer(
        callback,
        "원하시는 메뉴를 선택해주세요:",
        reply_markup=kbd.main_menu_inline()
    )

# --- SOZLAMALAR MENYUSI ---
@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    name, hourly_rate, tax_rate, work_days = await db.get_user_full_info(user_id)
    
    text = f"""⚙️ 현재 설정

💰 시급: {hourly_rate:,}원
📉 세금: {tax_rate}%
📅 근무요일: {work_days}

수정할 항목을 선택하세요:
"""
    await safe_edit_or_answer(callback, text, reply_markup=kbd.settings_inline())

# --- SOATLIK TO'LOV ---
@router.callback_query(F.data == "edit_rate")
async def edit_rate_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("💰 새로운 시급을 입력하세요 (예: 12500):")
    await state.set_state(Form.edit_rate)

@router.message(Form.edit_rate)
async def process_edit_rate(message: Message, state: FSMContext):
    try:
        new_rate = float(message.text.replace(',', '').replace('원', '').strip())
        user_id = message.from_user.id
        
        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute(
                "UPDATE users SET hourly_rate = ? WHERE user_id = ?",
                (new_rate, user_id)
            )
            await conn.commit()
        
        await message.answer(
            f"✅ 시급이 {new_rate:,}원으로 변경되었습니다!",
            reply_markup=kbd.main_menu_inline()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ 올바른 숫자를 입력해주세요.")

# --- SOLIQ ---
@router.callback_query(F.data == "edit_tax")
async def edit_tax_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("📉 새로운 세금율을 입력하세요 (예: 3.3):")
    await state.set_state(Form.edit_tax)

@router.message(Form.edit_tax)
async def process_edit_tax(message: Message, state: FSMContext):
    try:
        new_tax = float(message.text.replace(',', '.').replace('%', '').strip())
        user_id = message.from_user.id
        
        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute(
                "UPDATE users SET tax_rate = ? WHERE user_id = ?",
                (new_tax, user_id)
            )
            await conn.commit()
        
        await message.answer(
            f"✅ 세금율이 {new_tax}%로 변경되었습니다!",
            reply_markup=kbd.main_menu_inline()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ 올바른 숫자를 입력해주세요.")

# --- ISH KUNLARI ---
@router.callback_query(F.data == "edit_workdays")
async def edit_workdays_start(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    name, hourly_rate, tax_rate, work_days = await db.get_user_full_info(user_id)
    selected_days = work_days.split(',') if work_days else []
    
    await safe_edit_or_answer(
        callback,
        "📅 근무하는 요일을 선택하세요:",
        reply_markup=kbd.weekdays_inline(selected_days)
    )

@router.callback_query(F.data.startswith("toggle_day_"))
async def toggle_workday(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    day = callback.data.split("_")[-1]
    
    name, hourly_rate, tax_rate, work_days = await db.get_user_full_info(user_id)
    selected_days = work_days.split(',') if work_days else []
    
    if day in selected_days:
        selected_days.remove(day)
    else:
        selected_days.append(day)
    
    new_work_days = ','.join(selected_days)
    
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute(
            "UPDATE users SET work_days = ? WHERE user_id = ?",
            (new_work_days, user_id)
        )
        await conn.commit()
    
    try:
        await callback.message.edit_reply_markup(
            reply_markup=kbd.weekdays_inline(selected_days)
        )
    except:
        pass

@router.callback_query(F.data == "save_settings")
async def save_workdays(callback: CallbackQuery):
    await callback.answer("✅ 저장되었습니다!")
    await safe_edit_or_answer(
        callback,
        "원하시는 메뉴를 선택해주세요:",
        reply_markup=kbd.main_menu_inline()
    )

# --- KUNLIK TAHRIRLASH ---
@router.callback_query(F.data == "edit_logs")
async def show_edit_logs(callback: CallbackQuery):
    """Ishxonalarni ko'rsatish yoki to'g'ridan kalendar"""
    await callback.answer()
    user_id = callback.from_user.id
    
    # Foydalanuvchining barcha ishxonalarini olish
    workplaces = await db.get_user_workplaces(user_id)
    
    if not workplaces:
        # Ishxona yo'q - xabar ko'rsatish
        await safe_edit_or_answer(
            callback,
            "🏢 직장이 없습니다.\n먼저 직장을 추가하세요:",
            reply_markup=kbd.add_workplace_only_inline()
        )
        return
    
    if len(workplaces) == 1:
        # Bitta ishxona - to'g'ridan kalendar ko'rsatish
        workplace_id = workplaces[0][0]
        await show_calendar_for_workplace(callback, workplace_id)
        return
    
    # Bir nechta ishxona bo'lsa, tanlash uchun ro'yxat ko'rsatish
    await safe_edit_or_answer(
        callback,
        "🏢 수정할 직장을 선택하세요:",
        reply_markup=kbd.workplaces_for_edit_inline(workplaces)
    )

@router.callback_query(F.data.startswith("edit_logs_"))
async def show_calendar_for_workplace(callback: CallbackQuery, workplace_id: int = None):
    """Tanlangan ishxona uchun kalendar ko'rsatish"""
    await callback.answer()
    
    # Agar workplace_id parameter orqali kelmasa, callback datadan olish
    if workplace_id is None:
        workplace_id = int(callback.data.split("_")[-1])
    
    user_id = callback.from_user.id
    workplace_name = await db.get_workplace_name(workplace_id)
    now = datetime.now()
    
    # Ishlangan kunlarni olish (shu ishxona uchun)
    current_month = now.strftime('%Y-%m')
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute(
            """SELECT work_date, hours FROM work_logs 
               WHERE user_id = ? AND workplace_id = ? AND work_date LIKE ?""",
            (user_id, workplace_id, f"{current_month}%")
        ) as cursor:
            work_data = await cursor.fetchall()
    
    # Kalendar yaratish
    calendar_markup = await create_user_calendar_with_work(work_data, now, workplace_id)
    
    await safe_edit_or_answer(
        callback,
        f"🏢 {workplace_name}\n📅 {now.year}년 {now.month}월\n수정할 날짜를 선택하세요:\n\n• = 근무 기록됨 | 🏖 = 휴무",
        reply_markup=calendar_markup
    )

async def create_user_calendar_with_work(work_data, now, workplace_id):
    """Ishxona ID bilan kalendar yaratish"""
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
        if day in worked_days:
            hours = worked_days[day]
            if hours == 0:
                text = f"🏖{day}"
            else:
                text = f"•{day}"
        elif day == current_day:
            text = f"🔹{day}"
        else:
            text = str(day)
        
        buttons.append(InlineKeyboardButton(
            text=text, 
            callback_data=f"edit_day_{workplace_id}_{day}"
        ))
        
    # 7 tadan guruplash
    for i in range(0, len(buttons), 7):
        builder.row(*buttons[i:i+7])
    
    # Orqaga qaytish
    builder.row(InlineKeyboardButton(text="⬅️ 뒤로", callback_data="main_menu"))
    
    return builder.as_markup()

# --- KUNNI TAHRIRLASH ---
@router.callback_query(F.data.startswith("edit_day_"))
async def edit_day(callback: CallbackQuery):
    """Kunni tahrirlash - soatlarni tanlash"""
    await callback.answer()
    
    parts = callback.data.split("_")
    workplace_id = int(parts[2])
    day = parts[3]
    
    await safe_edit_or_answer(
        callback,
        f"📅 {day}일 근무 시간을 선택하세요:",
        reply_markup=kbd.select_hours_inline(day, workplace_id)
    )

# --- SOATNI SAQLASH ---
@router.callback_query(F.data.startswith("save_"))
async def save_hours(callback: CallbackQuery):
    await callback.answer()
    
    parts = callback.data.split("_")
    workplace_id = int(parts[1])
    day = parts[2]
    hours_str = parts[3]
    
    hours_float = float(hours_str)
    user_id = callback.from_user.id
    work_date = datetime.now().strftime(f"%Y-%m-{int(day):02d}")
    
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute("""
            INSERT INTO work_logs (user_id, workplace_id, work_date, hours) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, workplace_id, work_date) DO UPDATE SET hours = excluded.hours
        """, (user_id, workplace_id, work_date, hours_float))
        await conn.commit()
    
    if hours_float == 0:
        await callback.answer(f"✅ {day}일 휴무로 저장되었습니다!")
    else:
        await callback.answer(f"✅ {day}일 {hours_str}시간 저장완료!")

    await show_calendar_for_workplace(callback, workplace_id)

# --- QO'LDA KIRITISH ---
@router.callback_query(F.data.startswith("manual_edit_"))
async def manual_input_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    parts = callback.data.split("_")
    workplace_id = int(parts[2])
    day = parts[3]
    
    await state.update_data(workplace_id=workplace_id, editing_day=day)
    await callback.message.answer(f"⌨️ {day}일 근무 시간을 입력해주세요 (예: 9.5):")
    await state.set_state(Form.edit_manual_workplace_day)

@router.message(Form.edit_manual_workplace_day)
async def process_manual_input(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        workplace_id = data.get("workplace_id")
        day = data.get("editing_day")
        hours = float(message.text.replace(',', '.'))
        
        if hours < 0 or hours > 24:
            await message.answer("❌ 0-24 사이의 시간을 입력해주세요.")
            return
        
        user_id = message.from_user.id
        work_date = datetime.now().strftime(f"%Y-%m-{int(day):02d}")

        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute("""
                INSERT INTO work_logs (user_id, workplace_id, work_date, hours) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, workplace_id, work_date) DO UPDATE SET hours = excluded.hours
            """, (user_id, workplace_id, work_date, hours))
            await conn.commit()

        await message.answer(
            f"✅ {day}일 {hours}시간 저장완료!", 
            reply_markup=kbd.main_menu_inline()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ 숫자만 입력해주세요.")

# --- KUNLIK HISOBOT ---
@router.callback_query(F.data == "view_report")
async def view_report(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
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
            SELECT hourly_rate, tax_rate FROM users WHERE user_id = ?
        """, (user_id,)) as c:
            settings = await c.fetchone()
            hourly_rate = settings[0] if settings else 12500
            tax_rate = settings[1] if settings else 3.3

    if not rows:
        text = f"📅 {now.month}월 근무 기록이 없습니다."
    else:
        report_lines = [f"📅 {now.month}월 근무 상세 기록\n"]
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

    await safe_edit_or_answer(
        callback,
        text,
        reply_markup=kbd.main_menu_inline()
    )

# --- KUNLIK AVTOMATIK SO'ROV ---
@router.callback_query(F.data.startswith("daily_report_"))
async def process_daily_report(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    parts = callback.data.split("_")
    
    if parts[-1] == "manual":
        await callback.message.answer("⌨️ 어제 근무 시간을 입력해주세요 (예: 10.5):")
        await state.set_state(Form.daily_manual_input)
        return
    
    hours = float(parts[-1])
    user_id = callback.from_user.id
    
    yesterday = datetime.now() - timedelta(days=1)
    work_date = yesterday.strftime("%Y-%m-%d")

    # Foydalanuvchining ishxonasini olish (birinchi ishxona)
    workplaces = await db.get_user_workplaces(user_id)
    workplace_id = workplaces[0][0] if workplaces else None

    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute("""
            INSERT INTO work_logs (user_id, workplace_id, work_date, hours) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, workplace_id, work_date) DO UPDATE SET hours = excluded.hours
        """, (user_id, workplace_id, work_date, hours))
        await conn.commit()

    if hours == 0:
        await callback.answer("✅ 휴무로 기록되었습니다!")
        await safe_edit_or_answer(
            callback,
            f"✅ 어제 ({yesterday.month}월 {yesterday.day}일) 휴무로 저장되었습니다.",
            reply_markup=kbd.main_menu_inline()
        )
    else:
        await callback.answer(f"✅ {hours}시간 기록되었습니다!")
        await safe_edit_or_answer(
            callback,
            f"✅ 어제 ({yesterday.month}월 {yesterday.day}일) {hours}시간이 저장되었습니다.",
            reply_markup=kbd.main_menu_inline()
        )

@router.message(Form.daily_manual_input)
async def process_daily_manual(message: Message, state: FSMContext):
    try:
        hours = float(message.text.replace(',', '.'))
        
        if hours < 0 or hours > 24:
            await message.answer("❌ 0-24 사이의 시간을 입력해주세요.")
            return
        
        user_id = message.from_user.id
        yesterday = datetime.now() - timedelta(days=1)
        work_date = yesterday.strftime("%Y-%m-%d")

        # Foydalanuvchining ishxonasini olish
        workplaces = await db.get_user_workplaces(user_id)
        workplace_id = workplaces[0][0] if workplaces else None

        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute("""
                INSERT INTO work_logs (user_id, workplace_id, work_date, hours) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, workplace_id, work_date) DO UPDATE SET hours = excluded.hours
            """, (user_id, workplace_id, work_date, hours))
            await conn.commit()

        await message.answer(
            f"✅ 어제 ({yesterday.month}월 {yesterday.day}일) {hours}시간이 저장되었습니다!",
            reply_markup=kbd.main_menu_inline()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ 숫자만 입력해주세요.")

# --- FOYDALANUVCHI MA'LUMOTLARI ---
@router.message(F.text == "내 정보")
async def user_info(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "없음"
    full_name = message.from_user.full_name
    
    name, hourly_rate, tax_rate, work_days = await db.get_user_full_info(user_id)
    
    now = datetime.now()
    current_month = now.strftime('%Y-%m')
    
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute("""
            SELECT SUM(hours) FROM work_logs 
            WHERE user_id = ? AND work_date LIKE ?
        """, (user_id, f"{current_month}%")) as c:
            result = await c.fetchone()
            total_hours = result[0] if result[0] else 0

    text = f"""👤 내 정보

📱 이름: {full_name}
🆔 사용자명: @{username}
🔢 ID: {user_id}

⚙️ 설정
💰 시급: {hourly_rate:,}원
📉 세금: {tax_rate}%
📅 근무요일: {work_days}

📊 이번 달
⏱ 총 근무시간: {total_hours}시간
💵 예상 실수령액: {(total_hours * hourly_rate * (1 - tax_rate/100)):,.0f}원
"""
    
    await message.answer(text, parse_mode=None)
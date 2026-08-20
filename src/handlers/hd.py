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
    edit_schedule_manual = State()  # YANGI: 근무요일 수정 ichida qo'lda soat kiritish

# ===== HELPER FUNKSIYA =====
async def safe_edit_or_answer(callback, text, reply_markup=None, parse_mode=None):
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except:
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

def get_weekday_korean(date_obj):
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    return weekdays[date_obj.weekday()]

# --- START ---
@router.message(F.text == "/start")
async def cmd_start(message: Message):
    user_id = message.from_user.id
    await db.update_user_info(user_id, message.from_user.full_name, message.from_user.username)

    if not await db.is_user_active(user_id):
        await message.answer("🚫 차단된 사용자입니다.\n관리자에게 문의하세요.")
        return

    await message.answer("원하시는 메뉴를 선택해주세요:", reply_markup=kbd.main_menu_inline())

@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await safe_edit_or_answer(callback, "원하시는 메뉴를 선택해주세요:", reply_markup=kbd.main_menu_inline())

# --- SOZLAMALAR (프로필) ---
@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    name, hourly_rate, tax_rate, work_days = await db.get_user_full_info(user_id)

    text = f"""👤 프로필

⚙️ 현재 설정
━━━━━━━━━━━━━━━
💰 시급: {hourly_rate:,}원
📉 세금: {tax_rate}%
📅 근무요일: {work_days if work_days else '설정되지 않음'}
━━━━━━━━━━━━━━━

수정할 항목을 선택하세요:"""
    await safe_edit_or_answer(callback, text, reply_markup=kbd.settings_inline())

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
            await conn.execute("UPDATE users SET hourly_rate = ? WHERE user_id = ?", (new_rate, user_id))
            await conn.commit()

        await message.answer(f"✅ 시급이 {new_rate:,}원으로 변경되었습니다!", reply_markup=kbd.main_menu_inline())
        await state.clear()
    except ValueError:
        await message.answer("❌ 올바른 숫자를 입력해주세요.")

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
            await conn.execute("UPDATE users SET tax_rate = ? WHERE user_id = ?", (new_tax, user_id))
            await conn.commit()

        await message.answer(f"✅ 세금율이 {new_tax}%로 변경되었습니다!", reply_markup=kbd.main_menu_inline())
        await state.clear()
    except ValueError:
        await message.answer("❌ 올바른 숫자를 입력해주세요.")

# --- YANGI: 근무요일 수정 (kun + soat birga) ---
@router.callback_query(F.data == "edit_workdays")
async def edit_workdays_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id

    schedule = await db.get_user_schedule(user_id)

    if not schedule:
        # Eski work_days formatidan migratsiya (agar mavjud bo'lsa, default 10 soat)
        name, hourly_rate, tax_rate, work_days = await db.get_user_full_info(user_id)
        selected = work_days.split(',') if work_days else []
        schedule = {d: 10 for d in selected if d}

    await state.update_data(editing_schedule=schedule)

    await safe_edit_or_answer(
        callback,
        "📅 근무하는 요일과 근무시간을 선택하세요:\n\n요일을 눌러 켜고/끄고, 켜진 요일 아래에서 근무 시간을 선택하세요.",
        reply_markup=kbd.schedule_editor_inline(schedule)
    )

@router.callback_query(F.data.startswith("wd_toggle_"))
async def wd_toggle(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    day = callback.data.split("_")[-1]

    data = await state.get_data()
    schedule = data.get("editing_schedule", {})

    if schedule.get(day, 0) > 0:
        schedule[day] = 0
    else:
        schedule[day] = 10  # standart holat

    await state.update_data(editing_schedule=schedule)

    try:
        await callback.message.edit_reply_markup(reply_markup=kbd.schedule_editor_inline(schedule))
    except:
        pass

@router.callback_query(F.data.startswith("wd_hours_"))
async def wd_set_hours(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split("_")
    day = parts[2]
    hours = float(parts[3])

    data = await state.get_data()
    schedule = data.get("editing_schedule", {})
    schedule[day] = hours
    await state.update_data(editing_schedule=schedule)

    try:
        await callback.message.edit_reply_markup(reply_markup=kbd.schedule_editor_inline(schedule))
    except:
        pass

@router.callback_query(F.data.startswith("wd_manual_"))
async def wd_manual_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    day = callback.data.split("_")[-1]
    await state.update_data(manual_day=day)
    await callback.message.answer(f"⌨️ {day}요일 근무 시간을 입력하세요 (예: 9.5):")
    await state.set_state(Form.edit_schedule_manual)

@router.message(Form.edit_schedule_manual)
async def wd_manual_process(message: Message, state: FSMContext):
    try:
        hours = float(message.text.replace(',', '.'))
        if hours < 0 or hours > 24:
            await message.answer("❌ 0-24 사이의 시간을 입력해주세요.")
            return

        data = await state.get_data()
        schedule = data.get("editing_schedule", {})
        day = data.get("manual_day")
        schedule[day] = hours
        await state.update_data(editing_schedule=schedule)

        # Faqat matn kiritish holatidan chiqamiz, tanlangan schedule ma'lumoti saqlanadi
        await state.set_state(None)

        await message.answer(
            f"✅ {day}요일: {hours}시간으로 설정되었습니다.",
            reply_markup=kbd.schedule_editor_inline(schedule)
        )
    except ValueError:
        await message.answer("❌ 숫자만 입력해주세요.")

@router.callback_query(F.data == "wd_save")
async def wd_save(callback: CallbackQuery, state: FSMContext):
    await callback.answer("✅ 저장 중...")
    user_id = callback.from_user.id

    data = await state.get_data()
    schedule = data.get("editing_schedule", {})

    # 1. Jadvalni saqlash
    await db.save_user_schedule(user_id, schedule)

    # 2. Ishxonasi bo'lsa - shu oyni avtomatik to'ldirish
    workplaces = await db.get_user_workplaces(user_id)
    filled = False
    if workplaces:
        workplace_id = workplaces[0][0]
        await db.fill_month_from_schedule(user_id, workplace_id, schedule)
        filled = True

    await state.clear()

    if filled:
        text = "✅ 근무 일정이 저장되었습니다!\n📅 이번 달 근무표가 자동으로 채워졌습니다.\n\n원하시는 메뉴를 선택해주세요:"
    else:
        text = "✅ 근무 일정이 저장되었습니다!\n⚠️ 직장이 없어 자동 채우기는 건너뛰었습니다. 먼저 직장을 추가해주세요.\n\n원하시는 메뉴를 선택해주세요:"

    await safe_edit_or_answer(callback, text, reply_markup=kbd.main_menu_inline())

# --- TAHRIRLASH (근무표 수정) - o'zgarishsiz, mustaqil ishlaydi ---
@router.callback_query(F.data == "edit_logs")
async def show_edit_logs(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    workplaces = await db.get_user_workplaces(user_id)

    if not workplaces:
        await safe_edit_or_answer(callback, "🏢 직장이 없습니다.\n먼저 직장을 추가하세요:", reply_markup=kbd.add_workplace_only_inline())
        return

    if len(workplaces) == 1:
        workplace_id = workplaces[0][0]
        await show_calendar_for_workplace(callback, workplace_id)
        return

    await safe_edit_or_answer(callback, "🏢 수정할 직장을 선택하세요:", reply_markup=kbd.workplaces_for_edit_inline(workplaces))

@router.callback_query(F.data.startswith("edit_logs_"))
async def show_calendar_for_workplace(callback: CallbackQuery, workplace_id: int = None):
    await callback.answer()

    if workplace_id is None:
        workplace_id = int(callback.data.split("_")[-1])

    user_id = callback.from_user.id
    workplace_name = await db.get_workplace_name(workplace_id)
    now = datetime.now()

    current_month = now.strftime('%Y-%m')
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute(
            "SELECT work_date, hours FROM work_logs WHERE user_id = ? AND workplace_id = ? AND work_date LIKE ?",
            (user_id, workplace_id, f"{current_month}%")
        ) as cursor:
            work_data = await cursor.fetchall()

    calendar_markup = await create_user_calendar_with_work(work_data, now, workplace_id)

    await safe_edit_or_answer(
        callback,
        f"🏢 {workplace_name}\n📅 {now.year}년 {now.month}월\n수정할 날짜를 선택하세요:\n\n• = 근무 기록됨 | 🏖 = 휴무",
        reply_markup=calendar_markup
    )

async def create_user_calendar_with_work(work_data, now, workplace_id):
    builder = InlineKeyboardBuilder()

    year = now.year
    month = now.month

    worked_days = {}
    for date_str, hours in work_data:
        day = int(date_str.split('-')[-1])
        worked_days[day] = hours

    weekday_headers = ["월", "화", "수", "목", "금", "토", "일"]
    for header in weekday_headers:
        builder.button(text=header, callback_data="ignore")
    builder.adjust(7)

    first_day = datetime(year, month, 1)
    weekday = first_day.weekday()
    days_in_month = calendar.monthrange(year, month)[1]

    buttons = []
    for _ in range(weekday):
        buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

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

        buttons.append(InlineKeyboardButton(text=text, callback_data=f"edit_day_{workplace_id}_{day}"))

    # Oxirgi qatorni 7 ustunga to'liq to'ldirish (ustunlar siljib ketmasligi uchun)
    remainder = len(buttons) % 7
    if remainder != 0:
        for _ in range(7 - remainder):
            buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    for i in range(0, len(buttons), 7):
        builder.row(*buttons[i:i+7])

    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))

    return builder.as_markup()

@router.callback_query(F.data.startswith("edit_day_"))
async def edit_day(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    workplace_id = int(parts[2])
    day = parts[3]
    await safe_edit_or_answer(callback, f"📅 {day}일 근무 시간을 선택하세요:", reply_markup=kbd.select_hours_inline(day, workplace_id))

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
            ON CONFLICT(user_id, work_date) DO UPDATE SET 
                workplace_id = excluded.workplace_id,
                hours = excluded.hours
        """, (user_id, workplace_id, work_date, hours_float))
        await conn.commit()

    if hours_float == 0:
        await callback.answer(f"✅ {day}일 휴무로 저장되었습니다!")
    else:
        await callback.answer(f"✅ {day}일 {hours_str}시간 저장완료!")

    # Kalendarni qayta yuklash
    await show_calendar_for_workplace(callback, workplace_id)

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
                ON CONFLICT(user_id, work_date) DO UPDATE SET 
                    workplace_id = excluded.workplace_id,
                    hours = excluded.hours
            """, (user_id, workplace_id, work_date, hours))
            await conn.commit()

        await message.answer(f"✅ {day}일 {hours}시간 저장완료!", reply_markup=kbd.main_menu_inline())
        await state.clear()
    except ValueError:
        await message.answer("❌ 숫자만 입력해주세요.")

# --- DEFAULT HOLATGA QAYTARISH ---
@router.callback_query(F.data.startswith("clear_"))
async def clear_work_log(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    workplace_id = int(parts[1])
    day = parts[2]

    user_id = callback.from_user.id
    work_date = datetime.now().strftime(f"%Y-%m-{int(day):02d}")

    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute("""
            DELETE FROM work_logs 
            WHERE user_id = ? AND work_date = ? AND workplace_id = ?
        """, (user_id, work_date, workplace_id))
        await conn.commit()

    await callback.answer(f"✅ {day}일 기록이 삭제되었습니다!")

    await show_calendar_for_workplace(callback, workplace_id)

@router.callback_query(F.data == "view_report")
async def view_report(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    now = datetime.now()
    current_month = now.strftime('%Y-%m')

    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute(
            "SELECT work_date, hours FROM work_logs WHERE user_id = ? AND work_date LIKE ? ORDER BY work_date ASC",
            (user_id, f"{current_month}%")
        ) as c:
            rows = await c.fetchall()

        async with conn.execute("SELECT hourly_rate, tax_rate FROM users WHERE user_id = ?", (user_id,)) as c:
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

    await safe_edit_or_answer(callback, text, reply_markup=kbd.main_menu_inline())

# --- KUNLIK AVTOMATIK SO'ROV (soat 05:00 da) - fallback (ma'lumot mavjud bo'lmaganda) ---
@router.callback_query(F.data.startswith("daily_report_"))
async def process_daily_report(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")

    if parts[-1] == "manual":
        await callback.message.answer("⌨️ 오늘 근무 시간을 입력해주세요 (예: 10.5):")
        await state.set_state(Form.daily_manual_input)
        return

    hours = float(parts[-1])
    user_id = callback.from_user.id

    from datetime import datetime as dt
    import pytz

    seoul_tz = pytz.timezone("Asia/Seoul")
    today = dt.now(seoul_tz)
    work_date = today.strftime("%Y-%m-%d")

    workplaces = await db.get_user_workplaces(user_id)
    workplace_id = workplaces[0][0] if workplaces else 1

    await db.save_work_log_with_workplace(user_id, workplace_id, work_date, hours)

    if hours == 0:
        await callback.answer("✅ 휴무로 기록되었습니다!")
        await callback.message.edit_text(
            f"✅ 오늘 ({today.month}월 {today.day}일) 휴무로 저장되었습니다.",
            reply_markup=kbd.main_menu_inline()
        )
    else:
        await callback.answer(f"✅ {hours}시간 기록되었습니다!")
        await callback.message.edit_text(
            f"✅ 오늘 ({today.month}월 {today.day}일) {hours}시간이 저장되었습니다.",
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

        from datetime import datetime as dt
        import pytz

        seoul_tz = pytz.timezone("Asia/Seoul")
        today = dt.now(seoul_tz)
        work_date = today.strftime("%Y-%m-%d")

        workplaces = await db.get_user_workplaces(user_id)
        workplace_id = workplaces[0][0] if workplaces else 1

        await db.save_work_log_with_workplace(user_id, workplace_id, work_date, hours)

        await message.answer(
            f"✅ 오늘 ({today.month}월 {today.day}일) {hours}시간이 저장되었습니다!",
            reply_markup=kbd.main_menu_inline()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ 숫자만 입력해주세요.")

# --- YANGI: KUNLIK TASDIQLASH (jadval bo'yicha oldindan to'ldirilgan bo'lsa) ---
@router.callback_query(F.data.startswith("daily_confirm_"))
async def daily_confirm(callback: CallbackQuery):
    await callback.answer("✅ 확인되었습니다!")
    try:
        await callback.message.edit_text("✅ 확인되었습니다. 좋은 하루 되세요! 😊")
    except:
        pass

@router.callback_query(F.data.startswith("daily_change_"))
async def daily_change(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    workplace_id = int(parts[2])
    work_date = parts[3]  # "YYYY-MM-DD"
    day = str(int(work_date.split("-")[-1]))

    await safe_edit_or_answer(
        callback,
        f"📅 {day}일 근무 시간을 선택하세요:",
        reply_markup=kbd.select_hours_inline(day, workplace_id)
    )

@router.message(F.text.in_(["/info", "프로필", "내 정보"]))
async def user_info(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "없음"
    full_name = message.from_user.full_name
    name, hourly_rate, tax_rate, work_days = await db.get_user_full_info(user_id)
    now = datetime.now()
    current_month = now.strftime('%Y-%m')

    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute("SELECT SUM(hours) FROM work_logs WHERE user_id = ? AND work_date LIKE ?", (user_id, f"{current_month}%")) as c:
            result = await c.fetchone()
            total_hours = result[0] if result[0] else 0

    text = f"""👤 프로필

📱 이름: {full_name}
🆔 사용자명: @{username}
🔢 ID: {user_id}

⚙️ 설정
━━━━━━━━━━━━━━━
💰 시급: {hourly_rate:,}원
📉 세금: {tax_rate}%
📅 근무요일: {work_days if work_days else '설정되지 않음'}
━━━━━━━━━━━━━━━

📊 이번 달
⏱ 총 근무시간: {total_hours}시간
💵 예상 실수령액: {(total_hours * hourly_rate * (1 - tax_rate/100)):,.0f}원"""

    await message.answer(text, reply_markup=kbd.settings_inline())
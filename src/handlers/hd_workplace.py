from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
import calendar
from src.database import db
from src.keyboards import kbd

router = Router()

class AddWorkplaceForm(StatesGroup):
    name = State()

# /start command
@router.message(F.text == "/start")
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    await db.update_user_info(
        user_id,
        message.from_user.full_name,
        message.from_user.username
    )
    
    if not await db.is_user_active(user_id):
        await message.answer("🚫 차단된 사용자입니다.\n관리자에게 문의하세요.")
        return
    
    await message.answer(
        "원하시는 메뉴를 선택해주세요:",
        reply_markup=kbd.main_menu_inline()
    )

# /info command (내 정보)
@router.message(F.text.in_(["/info", "내 정보"]))
async def cmd_info(message: Message):
    user_id = message.from_user.id
    name, hourly_rate, tax_rate, work_days = await db.get_user_full_info(user_id)
    
    text = f"""ℹ️ 내 정보

👤 이름: {message.from_user.full_name or name}
💰 시급: {hourly_rate:,}원
📉 세금: {tax_rate}%
📅 근무요일: {work_days}
"""
    await message.answer(text, reply_markup=kbd.main_menu_inline())

# Asosiy menyuga qaytish
@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "원하시는 메뉴를 선택해주세요:",
        reply_markup=kbd.main_menu_inline()
    )

# 내 근무표 - ISHXONALAR RO'YXATI
@router.callback_query(F.data == "my_workplaces")
async def show_workplaces_list(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    
    workplaces = await db.get_user_workplaces(user_id)
    
    if not workplaces:
        await callback.message.edit_text(
            "🏢 직장이 없습니다.\n먼저 직장을 추가하세요:",
            reply_markup=kbd.add_workplace_only_inline()
        )
        return
    
    # Ishxonalar ro'yxati
    await callback.message.edit_text(
        "🏢 직장을 선택하세요:",
        reply_markup=kbd.workplaces_list_inline(workplaces)
    )

# Ishxona tanlash - MA'LUMOT KO'RSATISH
@router.callback_query(F.data.startswith("select_workplace_"))
async def show_workplace_report(callback: CallbackQuery):
    await callback.answer()
    workplace_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    
    workplace_name = await db.get_workplace_name(workplace_id)
    
    now = datetime.now()
    year = now.year
    month = now.month
    
    logs = await db.get_monthly_logs_by_workplace(user_id, workplace_id, year, month)
    work_dict = {log[0]: log[1] for log in logs}
    
    text = f"🏢 {workplace_name}\n📅 {month}월 근무 상세 기록\n\n"
    
    days_in_month = calendar.monthrange(year, month)[1]
    
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
        weekday = weekday_names[date_obj.weekday()]
        
        hours = work_dict.get(date_str, None)
        
        if hours is not None:
            if hours == 0:
                text += f"▫️ {day:02d}일 ({weekday}): 🏖 휴무\n"
            else:
                text += f"▫️ {day:02d}일 ({weekday}): {hours}시간\n"
    
    hourly_rate, tax_rate = await db.get_user_settings(user_id)
    total_hours = sum([log[1] for log in logs if log[1] > 0])
    gross = total_hours * hourly_rate
    tax = gross * (tax_rate / 100)
    net = gross - tax
    
    text += f"\n━━━━━━━━━━━━━━\n"
    text += f"⏱️ 총 근무시간: {total_hours}시간\n"
    text += f"💰 세전 급여: {gross:,.0f}원\n"
    text += f"📉 세금 ({tax_rate}%): {tax:,.0f}원\n"
    text += f"💵 실수령액: {net:,.0f}원"
    
    await callback.message.edit_text(
        text,
        reply_markup=kbd.workplace_actions_inline(workplace_id)
    )

# Yangi ishxona qo'shish
@router.callback_query(F.data == "add_new_workplace")
async def add_workplace_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("🏢 새 직장 이름을 입력하세요:")
    await state.set_state(AddWorkplaceForm.name)

@router.message(AddWorkplaceForm.name)
async def add_workplace_finish(message: Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    
    await db.add_workplace(user_id, name)
    await state.clear()
    
    workplaces = await db.get_user_workplaces(user_id)
    await message.answer(
        f"✅ '{name}' 직장이 추가되었습니다!",
        reply_markup=kbd.workplaces_list_inline(workplaces)
    )

# 월별 전체 보기 - ISHXONALAR RO'YXATI
@router.callback_query(F.data == "monthly_overview")
async def monthly_overview_workplaces(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    
    workplaces = await db.get_user_workplaces(user_id)
    
    if not workplaces:
        await callback.message.edit_text(
            "🏢 직장이 없습니다.",
            reply_markup=kbd.back_to_main_inline()
        )
        return
    
    await callback.message.edit_text(
        "🏢 직장을 선택하세요:",
        reply_markup=kbd.workplaces_for_monthly_inline(workplaces)
    )

# Ishxona tanlash (월별 uchun) - OYLAR
@router.callback_query(F.data.startswith("monthly_wp_"))
async def select_month_for_workplace(callback: CallbackQuery):
    await callback.answer()
    workplace_id = int(callback.data.split("_")[-1])
    workplace_name = await db.get_workplace_name(workplace_id)
    
    await callback.message.edit_text(
        f"🏢 {workplace_name}\n\n📅 월을 선택하세요:",
        reply_markup=kbd.select_month_inline(workplace_id)
    )

# Oy tanlash - MA'LUMOT
@router.callback_query(F.data.startswith("viewmonth_"))
async def view_selected_month(callback: CallbackQuery):
    await callback.answer()
    
    parts = callback.data.split("_")
    workplace_id = int(parts[1])
    year = int(parts[2])
    month = int(parts[3])
    
    user_id = callback.from_user.id
    workplace_name = await db.get_workplace_name(workplace_id)
    
    logs = await db.get_monthly_logs_by_workplace(user_id, workplace_id, year, month)
    work_dict = {log[0]: log[1] for log in logs}
    
    text = f"🏢 {workplace_name}\n📅 {year}년 {month}월 근무 상세 기록\n\n"
    
    days_in_month = calendar.monthrange(year, month)[1]
    
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
        weekday = weekday_names[date_obj.weekday()]
        
        hours = work_dict.get(date_str, None)
        
        if hours is not None:
            if hours == 0:
                text += f"▫️ {day:02d}일 ({weekday}): 🏖 휴무\n"
            else:
                text += f"▫️ {day:02d}일 ({weekday}): {hours}시간\n"
    
    hourly_rate, tax_rate = await db.get_user_settings(user_id)
    total_hours = sum([log[1] for log in logs if log[1] > 0])
    gross = total_hours * hourly_rate
    tax = gross * (tax_rate / 100)
    net = gross - tax
    
    text += f"\n━━━━━━━━━━━━━━\n"
    text += f"⏱️ 총 근무시간: {total_hours}시간\n"
    text += f"💰 세전 급여: {gross:,.0f}원\n"
    text += f"📉 세금 ({tax_rate}%): {tax:,.0f}원\n"
    text += f"💵 실수령액: {net:,.0f}원"
    
    await callback.message.edit_text(
        text,
        reply_markup=kbd.back_to_month_select_inline(workplace_id)
    )
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
import calendar
from src.database import db
from src.keyboards import kbd
from src.utils.state_filters import is_free_text
from aiogram.types import BufferedInputFile
from src.utils.image_generator import create_calendar_image
import asyncio

router = Router()

class AddWorkplaceForm(StatesGroup):
    name = State()

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

# Yordamchi funksiya - xabarni o'chirish
async def delete_message_after(bot, chat_id, message_id, seconds):
    """Xabarni berilgan soniyadan keyin o'chirish"""
    await asyncio.sleep(seconds)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

# /start command
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()

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

# Asosiy menyuga qaytish
@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await safe_edit_or_answer(
        callback,
        "원하시는 메뉴를 선택해주세요:",
        reply_markup=kbd.main_menu_inline()
    )

# 내 근무표 - ISHXONALAR RO'YXATI (yoki 1 ta bo'lsa to'g'ridan-to'g'ri hisobot)
@router.callback_query(F.data == "my_workplaces")
async def show_workplaces_list(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    user_id = callback.from_user.id

    workplaces = await db.get_user_workplaces(user_id)

    if not workplaces:
        await safe_edit_or_answer(
            callback,
            "🏢 직장이 없습니다.\n먼저 직장을 추가하세요:",
            reply_markup=kbd.add_workplace_only_inline()
        )
        return

    # YANGI: bitta ishxona bo'lsa - tanlash bosqichini o'tkazib yuborish
    if len(workplaces) == 1:
        await show_workplace_report(callback, workplace_id=workplaces[0][0])
        return

    # Ishxonalar ro'yxati
    await safe_edit_or_answer(
        callback,
        "🏢 직장을 선택하세요:",
        reply_markup=kbd.workplaces_list_inline(workplaces)
    )

# Ishxona tanlash - MA'LUMOT KO'RSATISH
@router.callback_query(F.data.startswith("select_workplace_"))
async def show_workplace_report(callback: CallbackQuery, workplace_id: int = None):
    await callback.answer()
    if workplace_id is None:
        workplace_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id

    workplace_name = await db.get_workplace_name(workplace_id)

    now = datetime.now()
    year = now.year
    month = now.month

    logs = await db.get_monthly_logs_by_workplace(user_id, workplace_id, year, month)
    # logs: [(work_date, hours, note), ...]
    work_dict = {log[0]: log[1] for log in logs}
    notes_dict = {log[0]: log[2] for log in logs if len(log) > 2 and log[2]}

    hourly_rate, tax_rate = await db.get_user_settings(user_id)
    total_hours = sum([log[1] for log in logs if log[1] > 0])
    gross = total_hours * hourly_rate
    tax = gross * (tax_rate / 100)
    net = gross - tax

    # Rasm yaratish (eslatmalar bilan birga)
    image = await create_calendar_image(
        workplace_name, month, year, 
        work_dict, total_hours, gross, tax, net,
        hourly_rate, tax_rate,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
        notes_dict=notes_dict
    )

    # Eski xabarni o'chirish
    try:
        await callback.message.delete()
    except:
        pass

    # Rasmni yuborish
    sent_message = await callback.message.answer_photo(
        photo=BufferedInputFile(image.read(), filename="calendar.png"),
        caption=f"🏢 {workplace_name}\n📅 {year}년 {month}월 근무표",
        reply_markup=kbd.workplace_actions_inline(workplace_id)
    )

    # 1 daqiqadan keyin rasmni o'chirish
    asyncio.create_task(delete_message_after(callback.message.bot, sent_message.chat.id, sent_message.message_id, 60))

# Yangi ishxona qo'shish
@router.callback_query(F.data == "add_new_workplace")
async def add_workplace_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("🏢 새 직장 이름을 입력하세요:")
    await state.set_state(AddWorkplaceForm.name)

@router.message(AddWorkplaceForm.name, is_free_text)
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

# Ishxonani o'chirish - ro'yxat ko'rsatish
@router.callback_query(F.data == "remove_workplace_list")
async def show_remove_workplace_list(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id

    workplaces = await db.get_user_workplaces(user_id)

    if not workplaces:
        await safe_edit_or_answer(
            callback,
            "🏢 직장이 없습니다.",
            reply_markup=kbd.back_to_main_inline()
        )
        return

    await safe_edit_or_answer(
        callback,
        "🗑 삭제할 직장을 선택하세요:\n\n⚠️ 직장을 삭제하면 해당 직장의 모든 근무 기록도 함께 삭제됩니다!",
        reply_markup=kbd.workplaces_remove_inline(workplaces)
    )

# Ishxonani o'chirishni tasdiqlash
@router.callback_query(F.data.startswith("confirm_remove_wp_"))
async def confirm_remove_workplace(callback: CallbackQuery):
    await callback.answer()
    workplace_id = int(callback.data.split("_")[-1])
    workplace_name = await db.get_workplace_name(workplace_id)

    await safe_edit_or_answer(
        callback,
        f"⚠️ '{workplace_name}' 직장을 삭제하시겠습니까?\n\n이 직장의 모든 근무 기록이 함께 삭제됩니다!",
        reply_markup=kbd.confirm_remove_workplace_inline(workplace_id)
    )

# Ishxonani o'chirish
@router.callback_query(F.data.startswith("delete_wp_"))
async def delete_workplace_confirmed(callback: CallbackQuery):
    await callback.answer()
    workplace_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id

    workplace_name = await db.get_workplace_name(workplace_id)
    await db.delete_workplace(workplace_id)

    workplaces = await db.get_user_workplaces(user_id)

    if not workplaces:
        await safe_edit_or_answer(
            callback,
            f"✅ '{workplace_name}' 직장이 삭제되었습니다.\n\n🏢 직장이 없습니다.\n먼저 직장을 추가하세요:",
            reply_markup=kbd.add_workplace_only_inline()
        )
    else:
        await safe_edit_or_answer(
            callback,
            f"✅ '{workplace_name}' 직장이 삭제되었습니다.\n\n🏢 직장을 선택하세요:",
            reply_markup=kbd.workplaces_list_inline(workplaces)
        )

# ===================== YANGI: 월별 전체 보기 (rasmsiz, bitta matnli xabar) =====================

@router.callback_query(F.data == "monthly_overview")
async def monthly_overview_workplaces(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id

    workplaces = await db.get_user_workplaces(user_id)

    if not workplaces:
        await safe_edit_or_answer(
            callback,
            "🏢 직장이 없습니다.",
            reply_markup=kbd.back_to_main_inline()
        )
        return

    # Bitta ishxona bo'lsa - to'g'ridan-to'g'ri to'liq tarixni ko'rsatish
    if len(workplaces) == 1:
        await show_full_monthly_summary(callback, workplaces[0][0])
        return

    await safe_edit_or_answer(
        callback,
        "🏢 직장을 선택하세요:",
        reply_markup=kbd.workplaces_for_monthly_inline(workplaces)
    )

# Ishxona tanlash (월별 uchun) - to'g'ridan-to'g'ri to'liq tarix
@router.callback_query(F.data.startswith("monthly_wp_"))
async def select_month_for_workplace(callback: CallbackQuery):
    await callback.answer()
    workplace_id = int(callback.data.split("_")[-1])
    await show_full_monthly_summary(callback, workplace_id)

async def show_full_monthly_summary(callback: CallbackQuery, workplace_id: int):
    """Barcha oylarning umumiy hisobotini bitta chiroyli matnli xabarda ko'rsatish"""
    user_id = callback.from_user.id
    text = await build_full_monthly_text(user_id, workplace_id)
    await safe_edit_or_answer(callback, text, reply_markup=kbd.back_to_main_inline())

async def build_full_monthly_text(user_id: int, workplace_id: int) -> str:
    """Berilgan ishxona bo'yicha barcha oylar hisobotini matn shaklida qaytaradi"""
    workplace_name = await db.get_workplace_name(workplace_id)
    hourly_rate, tax_rate = await db.get_user_settings(user_id)

    summaries = await db.get_all_monthly_summaries(user_id, workplace_id)

    if not summaries:
        return f"🏢 {workplace_name}\n\n📭 근무 기록이 없습니다."

    lines = [f"🏢 {workplace_name}", "📊 전체 근무 내역", "━━━━━━━━━━━━━━━━━━━━"]

    total_all_hours = 0
    total_all_net = 0

    for ym, total_hours, work_days_count in summaries:
        year, month = ym.split('-')
        gross = total_hours * hourly_rate
        tax = gross * (tax_rate / 100)
        net = gross - tax

        total_all_hours += total_hours
        total_all_net += net

        lines.append(f"\n🗓 {year}년 {int(month)}월")
        lines.append(f"　근무일 {work_days_count}일 · ⏱ {total_hours}시간")
        lines.append(f"　📉 세금 {tax:,.0f}원")
        lines.append(f"　💵 실수령 {net:,.0f}원")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📌 총 근무시간: {total_all_hours}시간")
    lines.append(f"📌 총 실수령(누적): {total_all_net:,.0f}원")

    text = "\n".join(lines)

    # Telegram xabar chegarasi (~4096 belgi)
    if len(text) > 4000:
        text = text[:3950] + "\n\n… (내역이 많아 일부만 표시됩니다)"

    return text

# YANGI: /monthly komandasi orqali (chap menyu / matn buyrug'i) kirish
@router.message(F.text.in_(["/monthly", "월별 전체 보기"]))
async def monthly_overview_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    workplaces = await db.get_user_workplaces(user_id)

    if not workplaces:
        await message.answer("🏢 직장이 없습니다.", reply_markup=kbd.back_to_main_inline())
        return

    if len(workplaces) == 1:
        text = await build_full_monthly_text(user_id, workplaces[0][0])
        await message.answer(text, reply_markup=kbd.back_to_main_inline())
        return

    await message.answer("🏢 직장을 선택하세요:", reply_markup=kbd.workplaces_for_monthly_inline(workplaces))
from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import calendar

# Pastki doimiy tugmalar
def main_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/start")],
            [KeyboardButton(text="프로필")]
        ],
        resize_keyboard=True
    )

# 1. Asosiy Inline menyu
def main_menu_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 내 근무표", callback_data="my_workplaces"))
    builder.row(InlineKeyboardButton(text="📅 월별 전체 보기", callback_data="monthly_overview"))
    return builder.as_markup()

# 1a. 내 근무표 ko'rsatilgandan keyin
def report_actions_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✏️ 근무표 수정", callback_data="edit_logs"))
    builder.row(InlineKeyboardButton(text="⚙️ 설정", callback_data="settings"))
    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))
    return builder.as_markup()

# 1b. Oylarni tanlash (eski, hozirda 월별 전체 보기 to'g'ridan-to'g'ri matn ko'rinishida)
def select_any_month_inline():
    builder = InlineKeyboardBuilder()
    now = datetime.now()

    for i in range(12):
        month_date = datetime(now.year, now.month, 1) - timedelta(days=30*i)
        month_text = month_date.strftime("%Y년 %m월")
        builder.button(
            text=month_text,
            callback_data=f"viewmonth_{month_date.year}_{month_date.month}"
        )

    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))
    return builder.as_markup()

# 1c. Oydan orqaga
def back_to_monthly_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ 뒤로", callback_data="monthly_overview"))
    return builder.as_markup()

# 2. Sozlamalar menyusi
def settings_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💰 시급 수정", callback_data="edit_rate"))
    builder.row(InlineKeyboardButton(text="📉 세금 수정", callback_data="edit_tax"))
    builder.row(InlineKeyboardButton(text="📅 근무요일 수정", callback_data="edit_workdays"))
    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))
    return builder.as_markup()

# 3. Hafta kunlari + har bir kun uchun soat birga tanlanadi - KVADRAT GRID (7 qator x 4 ustun)
def schedule_editor_inline(schedule: dict):
    """
    Sarlavha endi tugma emas - xabar matnida chiqadi (schedule_editor_header_text() ga qarang).
    Har bir hafta kuni uchun BITTA qatorda 4 ta bir xil kenglikdagi tugma:
    [ 월 ✅ ] [ 10 ] [ 10.5 ] [ ✏️ ]

    Kun ustunida faqat kun nomi + ✅/❌ - soat yozilmaydi (soat alohida ustunlarda).
    Agar kun ❌ (dam) bo'lsa - o'sha qatorda bo'sh (ko'rinmas) tugmalar qo'yiladi,
    shunda kun tugmasi cho'zilib ketmaydi va boshqalar bilan bir xil kenglikda,
    chap tomonda turadi.
    """
    days = ["월", "화", "수", "목", "금", "토", "일"]
    builder = InlineKeyboardBuilder()

    for d in days:
        hours = schedule.get(d, 0)
        is_active = hours and hours > 0

        # Kun ustunida endi soat ko'rsatilmaydi - faqat kun + holat
        day_label = f"{d} ✅" if is_active else f"{d} ❌"
        day_button = InlineKeyboardButton(text=day_label, callback_data=f"wd_toggle_{d}")

        if is_active:
            # Faol kun - 4 ta tugma bitta qatorda: [kun][10][10.5][✏️]
            mark_10 = "🔹" if hours == 10 else ""
            mark_105 = "🔹" if hours == 10.5 else ""

            builder.row(
                day_button,
                InlineKeyboardButton(text=f"{mark_10}10", callback_data=f"wd_hours_{d}_10"),
                InlineKeyboardButton(text=f"{mark_105}10.5", callback_data=f"wd_hours_{d}_10.5"),
                InlineKeyboardButton(text="✏️", callback_data=f"wd_manual_{d}"),
            )
        else:
            # Dam kuni - bo'sh tugmalar bilan kenglikni bir xil ushlab turamiz
            # (shunda kun tugmasi cho'zilib, o'rtaga surilib ketmaydi)
            builder.row(
                day_button,
                InlineKeyboardButton(text=" ", callback_data="ignore"),
                InlineKeyboardButton(text=" ", callback_data="ignore"),
                InlineKeyboardButton(text=" ", callback_data="ignore"),
            )

    builder.row(InlineKeyboardButton(text="💾 저장 완료 (이번 달 자동 반영)", callback_data="wd_save"))
    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))

    return builder.as_markup()


# 3a. schedule_editor_inline bilan birga yuboriladigan sarlavha matni (parse_mode="HTML")
def schedule_editor_header_text():
    """
    Klaviaturadan OLDIN xabar matni sifatida yuboriladigan sarlavha.
    <pre> ichida bo'lgani uchun ustunlar tekis, bir-biridan ajralib turadi.
    Handlerda: await message.answer(schedule_editor_header_text(), reply_markup=kbd.schedule_editor_inline(schedule), parse_mode="HTML")
    """
    return (
        "<b>근무 일정 설정</b>\n\n"
        "<pre>📅 근무요일      ⏰ 근무시간</pre>\n"
        "요일을 눌러 켜고/끄고, 시간을 선택하세요:"
    )

# 4. Kunlik so'rov uchun: mavjud belgilangan ma'lumotni tasdiqlash
def daily_confirm_inline(workplace_id, work_date):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ 맞습니다", callback_data=f"daily_confirm_{workplace_id}_{work_date}"),
        InlineKeyboardButton(text="✏️ 변경하기", callback_data=f"daily_change_{workplace_id}_{work_date}")
    )
    return builder.as_markup()

# 5. Kunlarni tahrirlash - KALENDAR ko'rinishda (eski, hali ham mavjud)
def edit_days_inline(workplace_id):
    """Oyning kunlarini hafta kunlari bilan kalendar ko'rinishida"""
    builder = InlineKeyboardBuilder()

    now = datetime.now()
    year = now.year
    month = now.month

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
        if day == current_day:
            text = f" 🔹{day}"
        else:
            text = str(day)

        buttons.append(InlineKeyboardButton(
            text=text, 
            callback_data=f"edit_day_{workplace_id}_{day}"
        ))

    # Oxirgi qatorni 7 ustunga to'liq to'ldirish (ustunlar siljib ketmasligi uchun)
    remainder = len(buttons) % 7
    if remainder != 0:
        for _ in range(7 - remainder):
            buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    for i in range(0, len(buttons), 7):
        builder.row(*buttons[i:i+7])

    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))

    return builder.as_markup()

# 6. Soatlarni tanlash - KVADRAT GRID, "시간" so'zisiz
def select_hours_inline(day, workplace_id):
    """Soat variantlari va dam olish kuni - 2 ustunli kvadrat grid"""
    builder = InlineKeyboardBuilder()

    builder.button(text="🏖 휴무", callback_data=f"save_{workplace_id}_{day}_0")

    standard_hours = [10, 10.5, 11]
    for hours in standard_hours:
        builder.button(
            text=f"{hours}",
            callback_data=f"save_{workplace_id}_{day}_{hours}"
        )

    builder.button(text="⌨️ 직접 입력", callback_data=f"manual_edit_{workplace_id}_{day}")
    builder.button(text="🔄 기록 삭제", callback_data=f"clear_{workplace_id}_{day}")

    # 2 ustunli kvadrat grid: [휴무][10] / [10.5][11] / [⌨️][🔄]
    builder.adjust(2, 2, 2)

    builder.row(
        InlineKeyboardButton(text="⬅️ 뒤로", callback_data=f"edit_logs_{workplace_id}")
    )

    return builder.as_markup()

# 7. Kunlik so'rov - soat 05:00 da (mavjud ma'lumot bo'lmaganda fallback)
def daily_report_inline():
    """Har kuni 05:00 da so'raladigan inline menu"""
    builder = InlineKeyboardBuilder()

    builder.button(text="🏖 휴무", callback_data="daily_report_0")

    standard_hours = [10, 10.5, 11]
    for hours in standard_hours:
        builder.button(
            text=f"{hours}",
            callback_data=f"daily_report_{hours}"
        )

    builder.button(text="⌨️ 직접 입력", callback_data="daily_report_manual")

    builder.adjust(2, 2, 1)

    return builder.as_markup()

# 8. Tasdiqlash
def confirm_inline(action, value=None):
    """Umumiy tasdiqlash tugmalari"""
    builder = InlineKeyboardBuilder()

    if value:
        callback_yes = f"confirm_{action}_{value}"
    else:
        callback_yes = f"confirm_{action}"

    builder.row(
        InlineKeyboardButton(text="✅ 예", callback_data=callback_yes),
        InlineKeyboardButton(text="❌ 아니오", callback_data="main_menu")
    )

    return builder.as_markup()

# Faqat +ADD tugmasi
def add_workplace_only_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ 직장 추가", callback_data="add_new_workplace"))
    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))
    return builder.as_markup()

# Ishxonalar ro'yxati (내 근무표 uchun)
def workplaces_list_inline(workplaces):
    builder = InlineKeyboardBuilder()
    for wp_id, wp_name in workplaces:
        builder.row(InlineKeyboardButton(
            text=f"🏢 {wp_name}",
            callback_data=f"select_workplace_{wp_id}"
        ))
    builder.row(
        InlineKeyboardButton(text="➕ 직장 추가", callback_data="add_new_workplace"),
        InlineKeyboardButton(text="🗑 직장 삭제", callback_data="remove_workplace_list")
    )
    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))
    return builder.as_markup()

# Ishxonani o'chirish uchun ro'yxat
def workplaces_remove_inline(workplaces):
    builder = InlineKeyboardBuilder()
    for wp_id, wp_name in workplaces:
        builder.row(InlineKeyboardButton(
            text=f"🗑 {wp_name}",
            callback_data=f"confirm_remove_wp_{wp_id}"
        ))
    builder.row(InlineKeyboardButton(text="⬅️ 뒤로", callback_data="my_workplaces"))
    return builder.as_markup()

# Ishxonani o'chirishni tasdiqlash
def confirm_remove_workplace_inline(workplace_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ 예, 삭제", callback_data=f"delete_wp_{workplace_id}"),
        InlineKeyboardButton(text="❌ 취소", callback_data="remove_workplace_list")
    )
    return builder.as_markup()

# Ishxonalar ro'yxati (월별 uchun)
def workplaces_for_monthly_inline(workplaces):
    builder = InlineKeyboardBuilder()
    for wp_id, wp_name in workplaces:
        builder.row(InlineKeyboardButton(
            text=f"🏢 {wp_name}",
            callback_data=f"monthly_wp_{wp_id}"
        ))
    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))
    return builder.as_markup()

# Ishxonalar ro'yxati (수정 uchun)
def workplaces_for_edit_inline(workplaces):
    builder = InlineKeyboardBuilder()
    for wp_id, wp_name in workplaces:
        builder.row(InlineKeyboardButton(
            text=f"🏢 {wp_name}",
            callback_data=f"edit_logs_{wp_id}"
        ))
    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))
    return builder.as_markup()

# Ishxona ma'lumoti ko'rsatilgandan keyin
def workplace_actions_inline(workplace_id):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✏️ 근무표 수정", callback_data=f"edit_logs_{workplace_id}"))
    builder.row(InlineKeyboardButton(text="⚙️ 설정", callback_data="settings"))
    builder.row(InlineKeyboardButton(text="⬅️ 뒤로", callback_data="my_workplaces"))
    return builder.as_markup()

# Oylarni tanlash (ishxona bo'yicha) - eski, endi ishlatilmaydi lekin xatolik chiqmasligi uchun qoldirilgan
def select_month_inline(workplace_id):
    builder = InlineKeyboardBuilder()
    now = datetime.now()

    for i in range(12):
        month_date = datetime(now.year, now.month, 1) - timedelta(days=30*i)
        month_text = month_date.strftime("%Y년 %m월")
        builder.button(
            text=month_text,
            callback_data=f"viewmonth_{workplace_id}_{month_date.year}_{month_date.month}"
        )

    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="⬅️ 뒤로", callback_data=f"monthly_wp_{workplace_id}"))
    return builder.as_markup()

# Oydan orqaga (ishxona tanlashga)
def back_to_month_select_inline(workplace_id):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ 뒤로", callback_data=f"monthly_wp_{workplace_id}"))
    return builder.as_markup()

# Faqat main menu
def back_to_main_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))
    return builder.as_markup()
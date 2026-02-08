from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import calendar

# Pastki doimiy tugmalar
def main_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/start")],
            [KeyboardButton(text="내 정보")]
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

# 1b. Oylarni tanlash (월별 전체 보기)
def select_any_month_inline():
    from datetime import datetime
    builder = InlineKeyboardBuilder()
    now = datetime.now()
    
    # Oxirgi 12 oy
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

# 3. Hafta kunlarini tanlash
def weekdays_inline(selected_days_list):
    days = ["월", "화", "수", "목", "금", "토", "일"]
    builder = InlineKeyboardBuilder()
    for d in days:
        status = "✅" if d in selected_days_list else "❌"
        builder.button(text=f"{d} {status}", callback_data=f"toggle_day_{d}")
    builder.adjust(4, 3)
    builder.row(InlineKeyboardButton(text="💾 저장 완료", callback_data="save_settings"))
    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))
    return builder.as_markup()

# 4. Kunlarni tahrirlash - KALENDAR ko'rinishda
def edit_days_inline():
    """Oyning kunlarini hafta kunlari bilan kalendar ko'rinishida"""
    builder = InlineKeyboardBuilder()
    
    now = datetime.now()
    year = now.year
    month = now.month
    
    # Hafta kunlari sarlavhasi
    weekday_headers = ["월", "화", "수", "목", "금", "토", "일"]
    for header in weekday_headers:
        builder.button(text=header, callback_data="ignore")
    builder.adjust(7)
    
    # Oyning birinchi kunini topish
    first_day = datetime(year, month, 1)
    # Python: Monday=0, Sunday=6; Biz: Monday=0, Sunday=6
    weekday = first_day.weekday()  # 0=Mon, 6=Sun
    
    # Oyning kunlar soni
    days_in_month = calendar.monthrange(year, month)[1]
    
    # Bo'sh joylar (oy boshlanishidan oldin)
    buttons = []
    for _ in range(weekday):
        buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
    
    # Kunlarni qo'shish
    current_day = now.day
    for day in range(1, days_in_month + 1):
        if day == current_day:
            text = f"📍{day}"
        else:
            text = str(day)
        
        buttons.append(InlineKeyboardButton(
            text=text, 
            callback_data=f"edit_day_{day}"
        ))
    
    # 7 tadan guruplash (hafta bo'yicha)
    for i in range(0, len(buttons), 7):
        builder.row(*buttons[i:i+7])
    
    # Orqaga qaytish
    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))
    
    return builder.as_markup()

# 5. Soatlarni tanlash - 휴무 bilan
def select_hours_inline(day):
    """Soat variantlari va dam olish kuni"""
    builder = InlineKeyboardBuilder()
    
    # 휴무 (Dam olish) tugmasi
    builder.row(InlineKeyboardButton(text="🏖 휴무", callback_data=f"save_{day}_0"))
    
    # Standart soatlar
    standard_hours = [10, 10.5, 11]
    for hours in standard_hours:
        builder.button(
            text=f"{hours}시간", 
            callback_data=f"save_{day}_{hours}"
        )
    
    builder.adjust(3)
    
    # Qo'lda kiritish va orqaga
    builder.row(
        InlineKeyboardButton(text="⌨️ 직접 입력", callback_data=f"manual_edit_{day}")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ 뒤로", callback_data="edit_logs")
    )
    
    return builder.as_markup()

# 6. Kunlik so'rov - soat 05:00 da
def daily_report_inline():
    """Har kuni 05:00 da so'raladigan inline menu"""
    builder = InlineKeyboardBuilder()
    
    # 휴무 tugmasi
    builder.row(InlineKeyboardButton(text="🏖 휴무", callback_data="daily_report_0"))
    
    # Standart soatlar
    standard_hours = [10, 10.5, 11]
    for hours in standard_hours:
        builder.button(
            text=f"{hours}시간", 
            callback_data=f"daily_report_{hours}"
        )
    
    builder.adjust(3)
    
    # Qo'lda kiritish
    builder.row(
        InlineKeyboardButton(text="⌨️ 직접 입력", callback_data="daily_report_manual")
    )
    
    return builder.as_markup()

# 7. Tasdiqlash
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
    builder.row(InlineKeyboardButton(text="➕ 직장 추가", callback_data="add_new_workplace"))
    builder.row(InlineKeyboardButton(text="⬅️ 메인으로", callback_data="main_menu"))
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

# Ishxona ma'lumoti ko'rsatilgandan keyin
def workplace_actions_inline(workplace_id):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✏️ 근무표 수정", callback_data="edit_logs"))
    builder.row(InlineKeyboardButton(text="⚙️ 설정", callback_data="settings"))
    builder.row(InlineKeyboardButton(text="⬅️ 뒤로", callback_data="my_workplaces"))
    return builder.as_markup()

# Oylarni tanlash (ishxona bo'yicha)
def select_month_inline(workplace_id):
    from datetime import datetime, timedelta
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
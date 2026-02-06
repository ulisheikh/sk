from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Admin panel - asosiy menyu
def admin_main_menu():
    """Admin panel asosiy menyusi"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👥 사용자 목록", callback_data="admin_users"))
    builder.row(InlineKeyboardButton(text="⬅️ 나가기", callback_data="main_menu"))
    return builder.as_markup()

# Foydalanuvchilar ro'yxati
def admin_users_list(users):
    """Foydalanuvchilar ro'yxati tugmalari"""
    builder = InlineKeyboardBuilder()
    
    for user in users:
        user_id, name, full_name, username, is_active, created_at = user
        
        # Ko'rsatiladigan nom
        display_name = full_name if full_name else (username if username else f"User {user_id}")
        
        # Status
        status = "✅" if is_active else "❌"
        
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {display_name}", 
                callback_data=f"admin_user_{user_id}"
            )
        )
    
    builder.row(InlineKeyboardButton(text="⬅️ 뒤로", callback_data="admin_panel"))
    return builder.as_markup()

# Foydalanuvchi boshqaruv menyusi
def admin_user_menu(user_id):
    """Tanlangan foydalanuvchi uchun boshqaruv menyusi"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="📅 근무표 보기", callback_data=f"admin_view_{user_id}"))
    builder.row(InlineKeyboardButton(text="✏️ 근무표 수정", callback_data=f"admin_edit_{user_id}"))
    builder.row(InlineKeyboardButton(text="⚙️ 설정 변경", callback_data=f"admin_settings_{user_id}"))
    builder.row(InlineKeyboardButton(text="🚫 사용자 차단", callback_data=f"admin_block_{user_id}"))
    builder.row(InlineKeyboardButton(text="🗑 사용자 삭제", callback_data=f"admin_delete_{user_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ 목록으로", callback_data="admin_users"))
    
    return builder.as_markup()

# Admin uchun sozlamalar menyusi
def admin_settings_menu(user_id):
    """Admin tomonidan foydalanuvchi sozlamalarini o'zgartirish"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="💰 시급 수정", callback_data=f"admin_rate_{user_id}"))
    builder.row(InlineKeyboardButton(text="📉 세금 수정", callback_data=f"admin_tax_{user_id}"))
    builder.row(InlineKeyboardButton(text="📅 근무요일 수정", callback_data=f"admin_workdays_{user_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ 뒤로", callback_data=f"admin_user_{user_id}"))
    
    return builder.as_markup()

# Admin uchun kalendar (foydalanuvchi tanlangan holda)
def admin_calendar_inline(user_id):
    """Admin uchun kalendar - foydalanuvchi ID bilan"""
    from datetime import datetime
    import calendar
    
    builder = InlineKeyboardBuilder()
    
    now = datetime.now()
    year = now.year
    month = now.month
    
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
    
    # Ishlangan kunlarni olish (faqat joriy oydan oldingi kunlar)
    import asyncio
    import aiosqlite
    from src.database import db as database
    
    worked_days = set()
    try:
        # Sync context ichida async funksiya ishlamaydi, shuning uchun statik ko'rinish
        # Bu funksiyani async qilib, handler ichida chaqirish kerak
        # Hozircha oddiy kalendar
        pass
    except:
        pass
    
    # Kunlarni qo'shish
    current_day = now.day
    for day in range(1, days_in_month + 1):
        if day == current_day:
            text = f"📍{day}"
        elif day < current_day:
            # Bugun dan oldingi kunlar - indicator kerak
            text = f"•{day}"  # Ishlagan kunlarda • belgisi
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

# Admin uchun soat tanlash
def admin_hours_inline(user_id, day):
    """Admin foydalanuvchi uchun soatlarni tanlaydi"""
    builder = InlineKeyboardBuilder()
    
    # 휴무
    builder.row(InlineKeyboardButton(text="🏖 휴무", callback_data=f"admin_save_{user_id}_{day}_0"))
    
    # Standart soatlar
    standard_hours = [10, 10.5, 11]
    for hours in standard_hours:
        builder.button(
            text=f"{hours}시간", 
            callback_data=f"admin_save_{user_id}_{day}_{hours}"
        )
    
    builder.adjust(3)
    
    # Qo'lda kiritish
    builder.row(
        InlineKeyboardButton(text="⌨️ 직접 입력", callback_data=f"admin_manual_{user_id}_{day}")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ 뒤로", callback_data=f"admin_edit_{user_id}")
    )
    
    return builder.as_markup()

# Admin uchun ish kunlarini tanlash
def admin_workdays_inline(user_id, selected_days_list):
    """Admin foydalanuvchi uchun ish kunlarini tanlaydi"""
    days = ["월", "화", "수", "목", "금", "토", "일"]
    builder = InlineKeyboardBuilder()
    
    for d in days:
        status = "✅" if d in selected_days_list else "❌"
        builder.button(
            text=f"{d} {status}", 
            callback_data=f"admin_toggle_{user_id}_{d}"
        )
    
    builder.adjust(4, 3)
    builder.row(
        InlineKeyboardButton(
            text="💾 저장 완료", 
            callback_data=f"admin_save_workdays_{user_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ 뒤로", 
            callback_data=f"admin_settings_{user_id}"
        )
    )
    
    return builder.as_markup()
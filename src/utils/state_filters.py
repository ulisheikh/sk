"""
FSM 'matn kutilmoqda' holatidagi handlerlar uchun umumiy filter.

Muammo: foydalanuvchi biror jarayonni (masalan 시급 수정) boshlab,
tugatmasdan boshqa buyruq yoki tugma bossa, bot hamon "raqam kutmoqda"
holatida qolib ketadi va keyingi /start, /info kabi buyruqlarni ham
xato deb qabul qiladi.

Yechim: shu filterni har bir "matn kiritishni kutuvchi" handlerga
qo'shib qo'yamiz. Agar kelgan xabar buyruq yoki menyu matni bo'lsa,
handler ishlamay o'tkazib yuboriladi va xabar haqiqiy (masalan /info)
handleriga yetib boradi.
"""
from aiogram.types import Message

RESERVED_TRIGGERS = {
    "/start", "/info", "/monthly", "/my_users",
    "프로필", "내 정보", "월별 전체 보기",
}

def is_free_text(message: Message) -> bool:
    """True bo'lsa - bu haqiqiy foydalanuvchi kiritgan qiymat (raqam va h.k),
    False bo'lsa - bu buyruq/menyu matni, FSM handler uni qabul qilmasligi kerak."""
    text = message.text or ""
    if text.startswith("/"):
        return False
    if text in RESERVED_TRIGGERS:
        return False
    return True
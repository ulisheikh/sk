"""
Middleware for checking if user is blocked
"""
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery, Message
from typing import Callable, Dict, Any, Awaitable
from src.database import db


class BlockedUserMiddleware(BaseMiddleware):
    """Bloklangan userlarni tekshirish middleware"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # User ID ni olish
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        
        # Admin emas va bloklangan bo'lsa
        if user_id and not db.is_admin(user_id):
            is_active = await db.is_user_active(user_id)
            if not is_active:
                # Bloklangan user
                if isinstance(event, Message):
                    await event.answer(
                        "🚫 차단된 사용자입니다.\n관리자에게 문의하세요.",
                        parse_mode=None
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "🚫 차단된 사용자입니다.",
                        show_alert=True
                    )
                return  # Handler chaqirilmaydi
        
        # Davom etish
        return await handler(event, data)
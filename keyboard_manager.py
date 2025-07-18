from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton from config import ROLE_OWNER, ROLE_SUPER_ADMIN, ROLE_ADMIN

def get_main_menu(role: str, user_id: str) -> InlineKeyboardMarkup: keyboard = InlineKeyboardMarkup()

if role == ROLE_OWNER:
    keyboard.add(InlineKeyboardButton(text="➕ افزودن ادمین ویژه", callback_data=f"add_super_admin:{user_id}"))
    keyboard.add(InlineKeyboardButton(text="➕ افزودن ادمین معمولی", callback_data=f"add_admin:{user_id}"))
    keyboard.add(InlineKeyboardButton(text="📢 لیست کانال‌ها", callback_data=f"list_channels:{user_id}"))
    keyboard.add(InlineKeyboardButton(text="👥 لیست گروه‌ها", callback_data=f"list_groups:{user_id}"))
    keyboard.add(InlineKeyboardButton(text="👤 لیست مدیران", callback_data=f"list_admins:{user_id}"))
    keyboard.add(InlineKeyboardButton(text="📝 ساخت لیست", callback_data=f"create_list:{user_id}"))

elif role == ROLE_SUPER_ADMIN:
    keyboard.add(InlineKeyboardButton(text="➕ افزودن ادمین معمولی", callback_data=f"add_admin:{user_id}"))
    keyboard.add(InlineKeyboardButton(text="👤 لیست مدیران", callback_data=f"list_admins:{user_id}"))
    keyboard.add(InlineKeyboardButton(text="📝 ساخت لیست", callback_data=f"create_list:{user_id}"))

elif role == ROLE_ADMIN:
    keyboard.add(InlineKeyboardButton(text="👤 لیست مدیران", callback_data=f"list_admins:{user_id}"))
    keyboard.add(InlineKeyboardButton(text="📝 ساخت لیست", callback_data=f"create_list:{user_id}"))

return keyboard

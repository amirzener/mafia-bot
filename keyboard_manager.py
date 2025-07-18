from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from access_control import AccessControl

class KeyboardManager:
    @staticmethod
    def get_main_menu(user_id):
        buttons = []
        if AccessControl.is_owner(user_id):
            buttons.append([InlineKeyboardButton("📢 مدیریت کانال‌ها", callback_data="manage_channels")])
            buttons.append([InlineKeyboardButton("🛠 مدیریت مدیران", callback_data="manage_admins")])
        elif AccessControl.is_super_admin(user_id):
            buttons.append([InlineKeyboardButton("🛠 مدیریت مدیران", callback_data="manage_admins")])

        buttons.append([InlineKeyboardButton("📋 ایجاد لیست جدید", callback_data="create_list")])

        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_admins_keyboard(user_id):
        buttons = []
        if AccessControl.is_owner(user_id):
            buttons.append([InlineKeyboardButton("➕ افزودن سوپرادمین", callback_data="add_super_admin")])

        buttons.append([InlineKeyboardButton("➕ افزودن ادمین", callback_data="add_admin")])
        buttons.append([InlineKeyboardButton("📋 لیست مدیران", callback_data="list_admins")])
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])

        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_channels_keyboard(user_id):
        buttons = [
            [InlineKeyboardButton("➕ افزودن کانال", callback_data="add_channel")],
            [InlineKeyboardButton("📋 لیست کانال‌ها", callback_data="list_channels")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_back_keyboard(target):
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 بازگشت", callback_data=f"back_to_{target}")]]
            )

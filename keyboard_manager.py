from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from data_manager import DataManager
from access_control import AccessControl
from config import ADMINS_FILE, CHANNELS_FILE, LISTS_FILE, ROLE_OWNER, ROLE_SUPER_ADMIN

class KeyboardManager:
    @staticmethod
    def get_main_menu(user_id):
        """منوی اصلی بات بر اساس سطح دسترسی کاربر"""
        buttons = []
        if AccessControl.is_owner(user_id):
            buttons.append([InlineKeyboardButton("📢 Manage Channels", callback_data="manage_channels")])
            buttons.append([InlineKeyboardButton("🛠 Manage Admins", callback_data="manage_admins")])
        elif AccessControl.is_super_admin(user_id):
            buttons.append([InlineKeyboardButton("🛠 Manage Admins", callback_data="manage_admins")])

        buttons.append([InlineKeyboardButton("📋 Create New List", callback_data="create_list")])  
        return InlineKeyboardMarkup(buttons)

    @staticmethod  
    def get_channels_keyboard():  
        """صفحه‌کلید مدیریت کانال‌ها"""
        channels = DataManager.load_data(CHANNELS_FILE)  
        buttons = [  
            [InlineKeyboardButton(f"🚪 Leave {info['title']}", callback_data=f"leave_{cid}")]  
            for cid, info in channels.items()  
        ]  
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])  
        return InlineKeyboardMarkup(buttons)

    @staticmethod  
    def get_admins_keyboard(user_id):  
        """صفحه‌کلید مدیریت ادمین‌ها"""
        buttons = []  
          
        if AccessControl.is_owner(user_id):  
            buttons.append([InlineKeyboardButton("➕ Add Super Admin", callback_data="add_super_admin")])  
          
        buttons.append([InlineKeyboardButton("➕ Add Admin", callback_data="add_admin")])  
        buttons.append([InlineKeyboardButton("📋 Admins List", callback_data="list_admins")])  
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])  
          
        return InlineKeyboardMarkup(buttons)

    @staticmethod  
    def get_admin_list_keyboard():  
        """صفحه‌کلید لیست ادمین‌ها"""
        admins = DataManager.load_data(ADMINS_FILE)  
        buttons = []  
          
        for uid, info in admins.items():  
            role_icon = "👑" if info["role"] == ROLE_OWNER else "🛡️" if info["role"] == ROLE_SUPER_ADMIN else "🛠️"  
            buttons.append([InlineKeyboardButton(  
                f"{role_icon} {info['name']} (ID: {uid})",   
                callback_data=f"admin_detail_{uid}"  
            )])  
          
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin_management")])  
        return InlineKeyboardMarkup(buttons)

    @staticmethod  
    def get_back_keyboard(target):  
        """صفحه‌کلید بازگشت"""
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"back_to_{target}")]])

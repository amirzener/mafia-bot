import os
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
import logging

# تنظیمات اولیه
OWNER_ID = 1305174339
BOT_TOKEN = "6990923109:AAEdRDVnU-YgIUMGh23RKJJiV1xHJZOfeEE"
WEBHOOK_URL = "https://mafia-bot-cq0h.onrender.com"
ADMINS_FILE = "admins.json"
GROUPS_FILE = "groups.json"
LISTS_FILE = "active_lists.json"
USERS_FILE = "users.json"

# سطوح دسترسی
ROLE_OWNER = "owner"
ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"

# حالت‌های مکالمه
GET_TIME, GET_ADMIN_INFO, GET_SUPER_ADMIN_INFO = range(3)

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DataManager:
    @staticmethod
    def load_data(filename, default=None):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default or {}

    @staticmethod
    def save_data(filename, data):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    @staticmethod
    def initialize_files():
        files = {
            ADMINS_FILE: {
                str(OWNER_ID): {
                    "name": "مالک",
                    "role": ROLE_OWNER
                }
            },
            GROUPS_FILE: {},
            LISTS_FILE: {},
            USERS_FILE: {}
        }
        for filename, default_data in files.items():
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    pass
            except FileNotFoundError:
                DataManager.save_data(filename, default_data)

class AccessControl:
    @staticmethod
    def is_owner(user_id):
        return str(user_id) == str(OWNER_ID)

    @staticmethod
    def is_super_admin(user_id):
        admins = DataManager.load_data(ADMINS_FILE)
        return str(user_id) in admins and admins[str(user_id)]["role"] == ROLE_SUPER_ADMIN

    @staticmethod
    def is_admin(user_id):
        admins = DataManager.load_data(ADMINS_FILE)
        return str(user_id) in admins and admins[str(user_id)]["role"] in [ROLE_ADMIN, ROLE_SUPER_ADMIN]

    @staticmethod
    def is_privileged(user_id):
        return AccessControl.is_owner(user_id) or AccessControl.is_admin(user_id)

class KeyboardManager:
    @staticmethod
    def get_main_menu(user_id):
        buttons = []
        if AccessControl.is_owner(user_id):
            buttons.append([InlineKeyboardButton("👥 مدیریت گروه‌ها", callback_data="manage_groups")])
            buttons.append([InlineKeyboardButton("🛠 مدیریت مدیران", callback_data="manage_admins")])
        elif AccessControl.is_super_admin(user_id):
            buttons.append([InlineKeyboardButton("🛠 مدیریت ادمین‌ها", callback_data="manage_admins")])
        
        buttons.append([InlineKeyboardButton("📋 ساخت لیست جدید", callback_data="create_list")])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_groups_keyboard():
        groups = DataManager.load_data(GROUPS_FILE)
        buttons = [
            [InlineKeyboardButton(f"🚪 خروج از {info['title']}", callback_data=f"leave_{gid}")]
            for gid, info in groups.items()
        ]
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_admins_keyboard(user_id):
        admins = DataManager.load_data(ADMINS_FILE)
        buttons = []
        
        if AccessControl.is_owner(user_id):
            buttons.append([InlineKeyboardButton("➕ افزودن مدیر ارشد", callback_data="add_super_admin")])
        
        buttons.append([InlineKeyboardButton("➕ افزودن ادمین", callback_data="add_admin")])
        buttons.append([InlineKeyboardButton("📋 لیست مدیران", callback_data="list_admins")])
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])
        
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_admin_list_keyboard():
        admins = DataManager.load_data(ADMINS_FILE)
        buttons = []
        
        for uid, info in admins.items():
            role_icon = "👑" if info["role"] == ROLE_OWNER else "🛡️" if info["role"] == ROLE_SUPER_ADMIN else "🛠️"
            buttons.append([InlineKeyboardButton(
                f"{role_icon} {info['name']} (آیدی: {uid})", 
                callback_data=f"admin_detail_{uid}"
            )])
        
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_admin_management")])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_admin_detail_keyboard(admin_id, current_user_id):
        buttons = []
        
        if not AccessControl.is_owner(admin_id) and current_user_id != admin_id:
            if AccessControl.is_owner(current_user_id) or (
                AccessControl.is_super_admin(current_user_id) and 
                not AccessControl.is_super_admin(admin_id)
            ):
                buttons.append([InlineKeyboardButton("❌ حذف مدیر", callback_data=f"remove_admin_{admin_id}")])
        
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_admin_list")])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_list_keyboard(list_id, is_privileged):
        buttons = [
            [
                InlineKeyboardButton("🎯 من هستم", callback_data=f"join_{list_id}"),
                InlineKeyboardButton("👁 ناظر می‌شوم", callback_data=f"observe_{list_id}")
            ]
        ]
        
        if is_privileged:
            buttons.append([InlineKeyboardButton("🚀 شروع بازی", callback_data=f"start_{list_id}")])
        
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_back_keyboard(target):
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=f"back_to_{target}")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        "🤖 ربات مدیریت لیست‌های بازی مافیا خوش آمدید!",
        reply_markup=KeyboardManager.get_main_menu(user_id)
    )

async def manage_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not AccessControl.is_owner(update.effective_user.id):
        await query.edit_message_text("❌ فقط مالک ربات می‌تواند گروه‌ها را مدیریت کند!")
        return
    
    groups = DataManager.load_data(GROUPS_FILE)
    if not groups:
        await query.edit_message_text(
            "⚠️ ربات در هیچ گروهی عضو نیست!",
            reply_markup=KeyboardManager.get_back_keyboard("main")
        )
        return
    
    message = "📋 لیست گروه‌ها و کانال‌ها:\n\n" + "\n\n".join(
        f"🏷 {info['title']}\n🆔 {gid}" for gid, info in groups.items()
    )
    
    await query.edit_message_text(
        message,
        reply_markup=KeyboardManager.get_groups_keyboard()
    )

async def leave_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    group_id = query.data.split('_')[1]
    groups = DataManager.load_data(GROUPS_FILE)
    
    if group_id not in groups:
        await query.answer("❌ گروه مورد نظر یافت نشد!", show_alert=True)
        return
    
    try:
        await context.bot.leave_chat(chat_id=int(group_id))
        groups.pop(group_id)
        DataManager.save_data(GROUPS_FILE, groups)
        await query.answer("✅ ربات از گروه خارج شد!", show_alert=True)
        await manage_groups(update, context)
    except Exception as e:
        logger.error(f"Error leaving group: {e}")
        await query.answer("❌ خطا در خروج از گروه!", show_alert=True)

async def manage_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if not AccessControl.is_privileged(user_id):
        await query.edit_message_text("❌ فقط مالک و مدیران می‌توانند مدیران را مدیریت کنند!")
        return
    
    await query.edit_message_text(
        "🛠 مدیریت مدیران و ادمین‌ها",
        reply_markup=KeyboardManager.get_admins_keyboard(user_id)
    )

async def add_super_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not AccessControl.is_owner(update.effective_user.id):
        await query.edit_message_text("❌ فقط مالک می‌تواند مدیر ارشد اضافه کند!")
        return
    
    await query.edit_message_text(
        "لطفاً شناسه عددی کاربر را برای مدیر ارشد شدن ارسال کنید:",
        reply_markup=KeyboardManager.get_back_keyboard("admin_management")
    )
    return GET_SUPER_ADMIN_INFO

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if not AccessControl.is_privileged(user_id):
        await query.edit_message_text("❌ فقط مالک و مدیران ارشد می‌توانند ادمین اضافه کنند!")
        return
    
    context.user_data['admin_role'] = ROLE_ADMIN if not AccessControl.is_owner(user_id) else None
    await query.edit_message_text(
        "لطفاً شناسه عددی کاربر را برای ادمین شدن ارسال کنید:",
        reply_markup=KeyboardManager.get_back_keyboard("admin_management")
    )
    return GET_ADMIN_INFO

async def get_admin_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.message.text.strip()
    
    if not admin_id.isdigit():
        await update.message.reply_text(
            "❌ شناسه باید یک عدد باشد! لطفاً دوباره ارسال کنید:",
            reply_markup=KeyboardManager.get_back_keyboard("admin_management")
        )
        return GET_ADMIN_INFO
    
    if admin_id == str(OWNER_ID):
        await update.message.reply_text(
            "❌ این کاربر مالک ربات است! لطفاً شناسه دیگری ارسال کنید:",
            reply_markup=KeyboardManager.get_back_keyboard("admin_management")
        )
        return GET_ADMIN_INFO
    
    admins = DataManager.load_data(ADMINS_FILE)
    if admin_id in admins:
        await update.message.reply_text(
            "❌ این کاربر از قبل مدیر است! لطفاً شناسه دیگری ارسال کنید:",
            reply_markup=KeyboardManager.get_back_keyboard("admin_management")
        )
        return GET_ADMIN_INFO
    
    context.user_data['new_admin_id'] = admin_id
    await update.message.reply_text(
        "لطفاً نام نمایشی مدیر را وارد کنید:",
        reply_markup=KeyboardManager.get_back_keyboard("admin_management")
    )
    return ConversationHandler.END

async def save_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_name = update.message.text.strip()
    admin_id = context.user_data['new_admin_id']
    role = context.user_data.get('admin_role', ROLE_ADMIN)
    
    admins = DataManager.load_data(ADMINS_FILE)
    admins[admin_id] = {
        "name": admin_name,
        "role": role
    }
    DataManager.save_data(ADMINS_FILE, admins)
    
    await update.message.reply_text(
        f"✅ مدیر جدید با موفقیت اضافه شد!\nنام: {admin_name}\nشناسه: {admin_id}\nسطح دسترسی: {'مدیر ارشد' if role == ROLE_SUPER_ADMIN else 'ادمین'}",
        reply_markup=KeyboardManager.get_back_keyboard("admin_management")
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    admins = DataManager.load_data(ADMINS_FILE)
    if not admins:
        await query.edit_message_text(
            "⚠️ هیچ مدیری ثبت نشده است!",
            reply_markup=KeyboardManager.get_back_keyboard("admin_management")
        )
        return
    
    await query.edit_message_text(
        "📋 لیست مدیران:",
        reply_markup=KeyboardManager.get_admin_list_keyboard()
    )

async def admin_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    admin_id = query.data.split('_')[2]
    admins = DataManager.load_data(ADMINS_FILE)
    
    if admin_id not in admins:
        await query.answer("❌ مدیر مورد نظر یافت نشد!", show_alert=True)
        return
    
    admin_info = admins[admin_id]
    role_text = "مالک" if admin_id == str(OWNER_ID) else "مدیر ارشد" if admin_info["role"] == ROLE_SUPER_ADMIN else "ادمین"
    
    await query.edit_message_text(
        f"👤 اطلاعات مدیر:\n\n"
        f"🆔 آیدی: {admin_id}\n"
        f"🏷 نام: {admin_info['name']}\n"
        f"🛡 سطح دسترسی: {role_text}",
        reply_markup=KeyboardManager.get_admin_detail_keyboard(admin_id, update.effective_user.id)
    )

async def remove_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    admin_id = query.data.split('_')[2]
    admins = DataManager.load_data(ADMINS_FILE)
    
    if admin_id not in admins:
        await query.answer("❌ مدیر مورد نظر یافت نشد!", show_alert=True)
        return
    
    if admin_id == str(OWNER_ID):
        await query.answer("❌ نمی‌توانید مالک را حذف کنید!", show_alert=True)
        return
    
    removed_name = admins.pop(admin_id)["name"]
    DataManager.save_data(ADMINS_FILE, admins)
    
    await query.answer(f"✅ مدیر {removed_name} حذف شد!", show_alert=True)
    await list_admins(update, context)

async def create_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    active_lists = DataManager.load_data(LISTS_FILE)
    for list_id, list_data in active_lists.items():
        if str(list_data["creator_id"]) == str(update.effective_user.id):
            await query.answer("⚠️ شما در حال حاضر یک لیست فعال دارید!", show_alert=True)
            return
    
    await query.edit_message_text(
        "⏰ لطفاً ساعت شروع بازی را به صورت 4 رقم (مثلاً 1930) ارسال کنید:",
        reply_markup=KeyboardManager.get_back_keyboard("main")
    )
    return GET_TIME

async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_input = update.message.text.strip()
    
    if not time_input.isdigit() or len(time_input) != 4:
        await update.message.reply_text(
            "❌ فرمت ساعت نامعتبر است! لطفاً ساعت را به صورت 4 رقم (مثلاً 1930) ارسال کنید:",
            reply_markup=KeyboardManager.get_back_keyboard("main")
        )
        return GET_TIME
    
    hour = int(time_input[:2])
    minute = int(time_input[2:])
    
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        await update.message.reply_text(
            "❌ زمان نامعتبر! لطفاً ساعت را به صورت صحیح وارد کنید (مثلاً 1930):",
            reply_markup=KeyboardManager.get_back_keyboard("main")
        )
        return GET_TIME
    
    # ایجاد لیست جدید
    list_id = str(len(DataManager.load_data(LISTS_FILE)) + 1)
    active_lists = DataManager.load_data(LISTS_FILE)
    
    active_lists[list_id] = {
        "creator_id": str(update.effective_user.id),
        "creator_name": update.effective_user.full_name,
        "time": f"{hour:02d}:{minute:02d}",
        "players": [],
        "observers": [],
        "channel_message_id": None,
        "group_message_ids": {}
    }
    
    DataManager.save_data(LISTS_FILE, active_lists)
    
    # ارسال لیست به کانال‌ها و گروه‌ها
    groups = DataManager.load_data(GROUPS_FILE)
    sent_to = []
    
    for chat_id, chat_info in groups.items():
        try:
            message = await update.message.bot.send_message(
                chat_id=chat_id,
                text=generate_list_text(list_id),
                reply_markup=KeyboardManager.get_list_keyboard(
                    list_id, 
                    AccessControl.is_privileged(update.effective_user.id)
                ),
                parse_mode="Markdown"
            )
            
            active_lists[list_id]["group_message_ids"][chat_id] = str(message.message_id)
            sent_to.append(chat_info['title'])
        except Exception as e:
            logger.error(f"Error sending list to chat {chat_id}: {e}")
    
    DataManager.save_data(LISTS_FILE, active_lists)
    
    await update.message.reply_text(
        f"✅ لیست بازی با موفقیت ایجاد شد و در {len(sent_to)} گروه/کانال ارسال شد:\n\n" +
        "\n".join(f"• {name}" for name in sent_to),
        reply_markup=KeyboardManager.get_back_keyboard("main")
    )
    
    return ConversationHandler.END

def generate_list_text(list_id):
    active_lists = DataManager.load_data(LISTS_FILE)
    if list_id not in active_lists:
        return "❌ لیست مورد نظر یافت نشد!"
    
    list_data = active_lists[list_id]
    rainbow_colors = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "⚫", "⚪"]
    
    text = (
        f"🌟 *𝑱𝑼𝑹𝑨𝑺𝑺𝑰𝑪 𝑴𝑨𝑭𝑰𝑨 𝑮𝑹𝑶𝑼𝑷𝑺* 🌟\n\n"
        f"⏰ ساعت شروع: {list_data['time']}\n"
        f"👤 سازنده: {list_data['creator_name']}\n\n"
        f"🎮 *بازیکنان:*\n" +
        ("\n".join(
            f"{rainbow_colors[i % len(rainbow_colors)]} {i+1}. [{player.split('|')[0]}](tg://user?id={player.split('|')[1]})"
            for i, player in enumerate(list_data['players'])
        ) if list_data['players'] else "هنوز کسی ثبت نام نکرده") +
        f"\n\n👁 *ناظرین:*\n" +
        ("\n".join(
            f"{i+1}. 👁 [{obs.split('|')[0]}](tg://user?id={obs.split('|')[1]})"
            for i, obs in enumerate(list_data['observers'])
        ) if list_data['observers'] else "هنوز ناظری ثبت نام نکرده")
    )
    
    return text

async def update_list_messages(list_id):
    active_lists = DataManager.load_data(LISTS_FILE)
    if list_id not in active_lists:
        return
    
    list_data = active_lists[list_id]
    list_text = generate_list_text(list_id)
    is_privileged = AccessControl.is_privileged(int(list_data['creator_id']))
    
    for chat_id, message_id in list_data['group_message_ids'].items():
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=int(message_id),
                text=list_text,
                reply_markup=KeyboardManager.get_list_keyboard(list_id, is_privileged),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error updating list message in chat {chat_id}: {e}")

async def join_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    list_id = query.data.split('_')[1]
    active_lists = DataManager.load_data(LISTS_FILE)
    
    if list_id not in active_lists:
        await query.answer("❌ این لیست منقضی شده!", show_alert=True)
        return
    
    user = update.effective_user
    user_info = f"{user.full_name}|{user.id}"
    
    # بررسی حضور در لیست ناظرین
    for obs in active_lists[list_id]['observers']:
        if obs.split('|')[1] == str(user.id):
            await query.answer("❌ شما در لیست ناظرین هستید و نمی‌توانید به بازیکنان بپیوندید!", show_alert=True)
            return
    
    # بررسی حضور قبلی در لیست بازیکنان
    for pl in active_lists[list_id]['players']:
        if pl.split('|')[1] == str(user.id):
            await query.answer("⚠️ شما قبلاً در لیست بازیکنان ثبت نام کرده‌اید!", show_alert=True)
            return
    
    active_lists[list_id]['players'].append(user_info)
    DataManager.save_data(LISTS_FILE, active_lists)
    
    # ذخیره کاربر
    users = DataManager.load_data(USERS_FILE)
    users[str(user.id)] = user.full_name
    DataManager.save_data(USERS_FILE, users)
    
    await query.answer("✅ به لیست بازیکنان اضافه شدید!", show_alert=True)
    await update_list_messages(list_id)

async def observe_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    list_id = query.data.split('_')[1]
    active_lists = DataManager.load_data(LISTS_FILE)
    
    if list_id not in active_lists:
        await query.answer("❌ این لیست منقضی شده!", show_alert=True)
        return
    
    if not AccessControl.is_privileged(update.effective_user.id):
        await query.answer("❌ فقط مدیران می‌توانند ناظر شوند!", show_alert=True)
        return
    
    user = update.effective_user
    user_info = f"{user.full_name}|{user.id}"
    
    # بررسی حضور در لیست بازیکنان
    for pl in active_lists[list_id]['players']:
        if pl.split('|')[1] == str(user.id):
            await query.answer("❌ شما در لیست بازیکنان هستید و نمی‌توانید ناظر شوید!", show_alert=True)
            return
    
    # بررسی حضور قبلی در لیست ناظرین
    for obs in active_lists[list_id]['observers']:
        if obs.split('|')[1] == str(user.id):
            await query.answer("⚠️ شما قبلاً به عنوان ناظر ثبت نام کرده‌اید!", show_alert=True)
            return
    
    if len(active_lists[list_id]['observers']) >= 2:
        await query.answer("❌ ظرفیت ناظرین تکمیل است!", show_alert=True)
        return
    
    active_lists[list_id]['observers'].append(user_info)
    DataManager.save_data(LISTS_FILE, active_lists)
    await query.answer("✅ به ناظرین اضافه شدید!", show_alert=True)
    await update_list_messages(list_id)

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    list_id = query.data.split('_')[1]
    active_lists = DataManager.load_data(LISTS_FILE)
    
    if list_id not in active_lists:
        await query.answer("❌ این لیست وجود ندارد!", show_alert=True)
        return
    
    list_data = active_lists[list_id]
    user_id = update.effective_user.id
    
    if str(user_id) != list_data["creator_id"] and not AccessControl.is_privileged(user_id):
        await query.answer("❌ فقط سازنده لیست یا مدیران می‌توانند بازی را شروع کنند!", show_alert=True)
        return
    
    if len(list_data['players']) < 5:
        await query.answer("❌ حداقل 5 بازیکن نیاز است!", show_alert=True)
        return
    
    # تگ کردن بازیکنان
    player_mentions = "\n".join(
        f"[{player.split('|')[0]}](tg://user?id={player.split('|')[1]})"
        for player in list_data['players']
    )
    
    observer_mentions = "\n".join(
        f"👁 [{obs.split('|')[0]}](tg://user?id={obs.split('|')[1]})"
        for obs in list_data['observers']
    ) if list_data['observers'] else "بدون ناظر"
    
    # ارسال پیام شروع بازی
    for chat_id in list_data['group_message_ids'].keys():
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🚀 *دوستان عزیز لابی زده شد تشریف بیارید*\n\n"
                    f"🎮 بازیکنان:\n{player_mentions}\n\n"
                    f"👁 ناظرین:\n{observer_mentions}\n\n"
                    f"𝑱𝑼𝑹𝑨𝑺𝑺𝑰𝑪 𝑴𝑨𝑭𝑰𝑨 𝑮𝑹𝑶𝑼𝑷𝑺"
                ),
                parse_mode="Markdown"
            )
            
            # حذف پیام لیست
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=int(list_data['group_message_ids'][chat_id])
            )
        except Exception as e:
            logger.error(f"Error sending start message to chat {chat_id}: {e}")
    
    # حذف لیست از فایل
    active_lists.pop(list_id)
    DataManager.save_data(LISTS_FILE, active_lists)
    
    await query.answer("✅ بازی با موفقیت شروع شد!", show_alert=True)

async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    target = query.data.split('_')[2]
    
    if target == "main":
        await query.edit_message_text(
            "🤖 ربات مدیریت لیست‌های بازی مافیا خوش آمدید!",
            reply_markup=KeyboardManager.get_main_menu(update.effective_user.id)
        )
    elif target == "admin_management":
        await manage_admins(update, context)
    elif target == "admin_list":
        await list_admins(update, context)

async def register_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        return
        
    chat = update.message.chat
    groups = DataManager.load_data(GROUPS_FILE)
    
    if str(chat.id) in groups:
        return
        
    groups[str(chat.id)] = {
        "title": chat.title,
        "type": chat.type
    }
    DataManager.save_data(GROUPS_FILE, groups)
    
    owner_msg = (
        f"🚀 ربات به گروه جدید اضافه شد:\n"
        f"🏷 نام: {chat.title}\n"
        f"🆔 آیدی: {chat.id}\n"
        f"📌 نوع: {'کانال' if chat.type == 'channel' else 'گروه'}"
    )
    
    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=owner_msg
        )
    except Exception as e:
        logger.error(f"Error sending message to owner: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.callback_query:
        try:
            await update.callback_query.answer("❌ خطایی رخ داد! لطفاً دوباره تلاش کنید.", show_alert=True)
        except:
            pass

def main():
    DataManager.initialize_files()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # مدیریت گروه‌ها
    app.add_handler(MessageHandler(filters.ChatType.GROUPS | filters.ChatType.CHANNELS, register_group))
    
    # مدیریت مدیران
    admin_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_super_admin, pattern="^add_super_admin$"),
            CallbackQueryHandler(add_admin, pattern="^add_admin$")
        ],
        states={
            GET_SUPER_ADMIN_INFO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_admin_info)
            ],
            GET_ADMIN_INFO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_admin_info)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(back_handler, pattern="^back_to_")
        ]
    )
    app.add_handler(admin_conv_handler)
    
    # مدیریت لیست‌ها
    list_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_list, pattern="^create_list$")],
        states={
            GET_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)]
        },
        fallbacks=[
            CallbackQueryHandler(back_handler, pattern="^back_to_")
        ]
    )
    app.add_handler(list_conv_handler)
    
    # دستورات اصلی
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(manage_groups, pattern="^manage_groups$"))
    app.add_handler(CallbackQueryHandler(manage_admins, pattern="^manage_admins$"))
    app.add_handler(CallbackQueryHandler(list_admins, pattern="^list_admins$"))
    app.add_handler(CallbackQueryHandler(admin_detail, pattern="^admin_detail_"))
    app.add_handler(CallbackQueryHandler(remove_admin_action, pattern="^remove_admin_"))
    app.add_handler(CallbackQueryHandler(leave_group, pattern="^leave_"))
    app.add_handler(CallbackQueryHandler(join_list, pattern="^join_"))
    app.add_handler(CallbackQueryHandler(observe_list, pattern="^observe_"))
    app.add_handler(CallbackQueryHandler(start_game, pattern="^start_"))
    app.add_handler(CallbackQueryHandler(back_handler, pattern="^back_to_"))
    
    # خطاها
    app.add_error_handler(error_handler)
    
    # تنظیم وب‌هوک
   app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 10000)),  # Render uses $PORT
    webhook_url=WEBHOOK_URL
)

if __name__ == '__main__':
    main()

import os
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
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

# Configuration
OWNER_ID = int(os.environ.get('OWNER_ID'))
BOT_TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
ADMINS_FILE = "admins.json"
CHANNELS_FILE = "channels.json"
LISTS_FILE = "active_lists.json"
USERS_FILE = "users.json"

# Role definitions
ROLE_OWNER = "owner"
ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"

# Conversation states
GET_TIME, GET_ADMIN_INFO, GET_SUPER_ADMIN_INFO = range(3)

# Setup logging
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
                    "name": "Owner",  
                    "role": ROLE_OWNER  
                }  
            },  
            CHANNELS_FILE: {},  
            LISTS_FILE: {},  
            USERS_FILE: {}  
        }  
        for filename, default_data in files.items():  
            if not os.path.exists(filename):
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
            buttons.append([InlineKeyboardButton("📢 Manage Channels", callback_data="manage_channels")])
            buttons.append([InlineKeyboardButton("🛠 Manage Admins", callback_data="manage_admins")])
        elif AccessControl.is_super_admin(user_id):
            buttons.append([InlineKeyboardButton("🛠 Manage Admins", callback_data="manage_admins")])

        buttons.append([InlineKeyboardButton("📋 Create New List", callback_data="create_list")])  
        return InlineKeyboardMarkup(buttons)  

    @staticmethod  
    def get_channels_keyboard():  
        channels = DataManager.load_data(CHANNELS_FILE)  
        buttons = [  
            [InlineKeyboardButton(f"🚪 Leave {info['title']}", callback_data=f"leave_{cid}")]  
            for cid, info in channels.items()  
        ]  
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])  
        return InlineKeyboardMarkup(buttons)  

    @staticmethod  
    def get_admins_keyboard(user_id):  
        admins = DataManager.load_data(ADMINS_FILE)  
        buttons = []  
          
        if AccessControl.is_owner(user_id):  
            buttons.append([InlineKeyboardButton("➕ Add Super Admin", callback_data="add_super_admin")])  
          
        buttons.append([InlineKeyboardButton("➕ Add Admin", callback_data="add_admin")])  
        buttons.append([InlineKeyboardButton("📋 Admins List", callback_data="list_admins")])  
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])  
          
        return InlineKeyboardMarkup(buttons)  

    @staticmethod  
    def get_admin_list_keyboard():  
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
    def get_admin_detail_keyboard(admin_id, current_user_id):  
        buttons = []  
          
        if not AccessControl.is_owner(admin_id) and current_user_id != admin_id:  
            if AccessControl.is_owner(current_user_id) or (  
                AccessControl.is_super_admin(current_user_id) and   
                not AccessControl.is_super_admin(admin_id)  
            ):  
                buttons.append([InlineKeyboardButton("❌ Remove Admin", callback_data=f"remove_admin_{admin_id}")])  
          
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin_list")])  
        return InlineKeyboardMarkup(buttons)  

    @staticmethod  
    def get_list_keyboard(list_id, is_privileged):  
        buttons = [  
            [  
                InlineKeyboardButton("🎯 Join Game", callback_data=f"join_{list_id}"),  
                InlineKeyboardButton("👁 Observe", callback_data=f"observe_{list_id}")  
            ]  
        ]  
          
        if is_privileged:  
            buttons.append([InlineKeyboardButton("🚀 Start Game", callback_data=f"start_{list_id}")])  
          
        return InlineKeyboardMarkup(buttons)  

    @staticmethod  
    def get_back_keyboard(target):  
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"back_to_{target}")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)
    await update.message.reply_text(
        "🤖 Welcome to Mafia Game List Management Bot!",
        reply_markup=KeyboardManager.get_main_menu(user_id)
    )

async def manage_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not AccessControl.is_owner(update.effective_user.id):  
        await query.edit_message_text("❌ Only the bot owner can manage channels!")  
        return  
    
    channels = DataManager.load_data(CHANNELS_FILE)  
    if not channels:  
        await query.edit_message_text(  
            "⚠️ Bot is not in any channels!",  
            reply_markup=KeyboardManager.get_back_keyboard("main")  
        )  
        return  
    
    message = "📋 Channel List:\n\n" + "\n\n".join(  
        f"🏷 {info['title']}\n🆔 {cid}" for cid, info in channels.items()  
    )  
    
    await query.edit_message_text(  
        message,  
        reply_markup=KeyboardManager.get_channels_keyboard()  
    )

async def leave_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    channel_id = query.data.split('_')[1]  
    channels = DataManager.load_data(CHANNELS_FILE)  
    
    if channel_id not in channels:  
        await query.answer("❌ Channel not found!", show_alert=True)  
        return  
    
    try:  
        await context.bot.leave_chat(chat_id=int(channel_id))  
        channels.pop(channel_id)  
        DataManager.save_data(CHANNELS_FILE, channels)  
        await query.answer("✅ Bot left the channel!", show_alert=True)  
        await manage_channels(update, context)  
    except Exception as e:  
        logger.error(f"Error leaving channel: {e}")  
        await query.answer("❌ Error leaving channel!", show_alert=True)

async def manage_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id  
    if not AccessControl.is_privileged(user_id):  
        await query.edit_message_text("❌ Only owner and admins can manage admins!")  
        return  
    
    await query.edit_message_text(  
        "🛠 Admin Management",  
        reply_markup=KeyboardManager.get_admins_keyboard(user_id)  
    )

async def add_super_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not AccessControl.is_owner(update.effective_user.id):  
        await query.edit_message_text("❌ Only owner can add super admins!")  
        return  
    
    await query.edit_message_text(  
        "Please send the user ID to be added as super admin:",  
        reply_markup=KeyboardManager.get_back_keyboard("admin_management")  
    )  
    return GET_SUPER_ADMIN_INFO

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id  
    if not AccessControl.is_privileged(user_id):  
        await query.edit_message_text("❌ Only owner and super admins can add admins!")  
        return  
    
    context.user_data['admin_role'] = ROLE_ADMIN if not AccessControl.is_owner(user_id) else None  
    await query.edit_message_text(  
        "Please send the user ID to be added as admin:",  
        reply_markup=KeyboardManager.get_back_keyboard("admin_management")  
    )  
    return GET_ADMIN_INFO

async def get_admin_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.message.text.strip()
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)

    if not admin_id.isdigit():  
        msg = await update.message.reply_text(  
            "❌ ID must be a number! Please try again:",  
            reply_markup=KeyboardManager.get_back_keyboard("admin_management")  
        )  
        context.user_data['last_msg'] = msg.message_id
        return GET_ADMIN_INFO  
    
    if admin_id == str(OWNER_ID):  
        msg = await update.message.reply_text(  
            "❌ This user is the bot owner! Please send another ID:",  
            reply_markup=KeyboardManager.get_back_keyboard("admin_management")  
        )  
        context.user_data['last_msg'] = msg.message_id
        return GET_ADMIN_INFO  
    
    admins = DataManager.load_data(ADMINS_FILE)  
    if admin_id in admins:  
        msg = await update.message.reply_text(  
            "❌ This user is already an admin! Please send another ID:",  
            reply_markup=KeyboardManager.get_back_keyboard("admin_management")  
        )  
        context.user_data['last_msg'] = msg.message_id
        return GET_ADMIN_INFO  
    
    context.user_data['new_admin_id'] = admin_id  
    msg = await update.message.reply_text(  
        "Please enter the admin's display name:",  
        reply_markup=KeyboardManager.get_back_keyboard("admin_management")  
    )  
    context.user_data['last_msg'] = msg.message_id
    return GET_ADMIN_INFO

async def save_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_name = update.message.text.strip()
    admin_id = context.user_data['new_admin_id']
    role = context.user_data.get('admin_role', ROLE_ADMIN)
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)

    admins = DataManager.load_data(ADMINS_FILE)  
    admins[admin_id] = {  
        "name": admin_name,  
        "role": role  
    }  
    DataManager.save_data(ADMINS_FILE, admins)  
    
    await update.message.reply_text(  
        f"✅ New admin added successfully!\nName: {admin_name}\nID: {admin_id}\nRole: {'Super Admin' if role == ROLE_SUPER_ADMIN else 'Admin'}",  
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
            "⚠️ No admins registered!",  
            reply_markup=KeyboardManager.get_back_keyboard("admin_management")  
        )  
        return  
    
    await query.edit_message_text(  
        "📋 Admins List:",  
        reply_markup=KeyboardManager.get_admin_list_keyboard()  
    )

async def admin_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    admin_id = query.data.split('_')[2]  
    admins = DataManager.load_data(ADMINS_FILE)  
    
    if admin_id not in admins:  
        await query.answer("❌ Admin not found!", show_alert=True)  
        return  
    
    admin_info = admins[admin_id]  
    role_text = "Owner" if admin_id == str(OWNER_ID) else "Super Admin" if admin_info["role"] == ROLE_SUPER_ADMIN else "Admin"  
    
    await query.edit_message_text(  
        f"👤 Admin Information:\n\n"  
        f"🆔 ID: {admin_id}\n"  
        f"🏷 Name: {admin_info['name']}\n"  
        f"🛡 Role: {role_text}",  
        reply_markup=KeyboardManager.get_admin_detail_keyboard(admin_id, update.effective_user.id)  
    )

async def remove_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    admin_id = query.data.split('_')[2]  
    admins = DataManager.load_data(ADMINS_FILE)  
    
    if admin_id not in admins:  
        await query.answer("❌ Admin not found!", show_alert=True)  
        return  
    
    if admin_id == str(OWNER_ID):  
        await query.answer("❌ Cannot remove owner!", show_alert=True)  
        return  
    
    removed_name = admins.pop(admin_id)["name"]  
    DataManager.save_data(ADMINS_FILE, admins)  
    
    await query.answer(f"✅ Admin {removed_name} removed!", show_alert=True)  
    await list_admins(update, context)

async def create_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    active_lists = DataManager.load_data(LISTS_FILE)  
    for list_id, list_data in active_lists.items():  
        if str(list_data["creator_id"]) == str(update.effective_user.id):  
            await query.answer("⚠️ You already have an active list!", show_alert=True)  
            return  
    
    await query.edit_message_text(  
        "⏰ Please enter the game start time in 24h format (e.g. 1930):",  
        reply_markup=KeyboardManager.get_back_keyboard("main")  
    )  
    return GET_TIME

async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_input = update.message.text.strip()
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)

    if not time_input.isdigit() or len(time_input) != 4:  
        msg = await update.message.reply_text(  
            "❌ Invalid time format! Please enter time as 4 digits (e.g. 1930):",  
            reply_markup=KeyboardManager.get_back_keyboard("main")  
        )  
        context.user_data['last_msg'] = msg.message_id
        return GET_TIME  
    
    hour = int(time_input[:2])  
    minute = int(time_input[2:])  
    
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:  
        msg = await update.message.reply_text(  
            "❌ Invalid time! Please enter a valid time (e.g. 1930):",  
            reply_markup=KeyboardManager.get_back_keyboard("main")  
        )  
        context.user_data['last_msg'] = msg.message_id
        return GET_TIME  
    
    # Create new list  
    list_id = str(len(DataManager.load_data(LISTS_FILE)) + 1)  
    active_lists = DataManager.load_data(LISTS_FILE)  
    
    active_lists[list_id] = {  
        "creator_id": str(update.effective_user.id),  
        "creator_name": update.effective_user.full_name,  
        "time": f"{hour:02d}:{minute:02d}",  
        "players": [],  
        "observers": [],  
        "channel_message_id": None  
    }  
    
    DataManager.save_data(LISTS_FILE, active_lists)  
    
    # Send list to channels  
    channels = DataManager.load_data(CHANNELS_FILE)  
    sent_to = []  
    
    for chat_id, chat_info in channels.items():  
        try:  
            message = await context.bot.send_message(  
                chat_id=chat_id,  
                text=generate_list_text(list_id),  
                reply_markup=KeyboardManager.get_list_keyboard(  
                    list_id,   
                    AccessControl.is_privileged(update.effective_user.id)  
                ),  
                parse_mode="Markdown"  
            )  
              
            active_lists[list_id]["channel_message_id"] = str(message.message_id)  
            sent_to.append(chat_info['title'])  
        except Exception as e:  
            logger.error(f"Error sending list to channel {chat_id}: {e}")  
    
    DataManager.save_data(LISTS_FILE, active_lists)  
    
    if 'last_msg' in context.user_data:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=context.user_data['last_msg'])
    
    await update.message.reply_text(  
        f"✅ Game list created successfully and sent to {len(sent_to)} channel(s):\n\n" +  
        "\n".join(f"• {name}" for name in sent_to),  
        reply_markup=KeyboardManager.get_back_keyboard("main")  
    )  
    
    context.user_data.clear()
    return ConversationHandler.END

def generate_list_text(list_id):
    active_lists = DataManager.load_data(LISTS_FILE)
    if list_id not in active_lists:
        return "❌ List not found!"

    list_data = active_lists[list_id]  
    rainbow_colors = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "⚫", "⚪"]  
    
    text = (  
        f"🌟 *JURASSIC MAFIA GAME* 🌟\n\n"  
        f"⏰ Start time: {list_data['time']}\n"  
        f"👤 Creator: {list_data['creator_name']}\n\n"  
        f"🎮 *Players:*\n" +  
        ("\n".join(  
            f"{rainbow_colors[i % len(rainbow_colors)]} {i+1}. [{player.split('|')[0]}](tg://user?id={player.split('|')[1]})"  
            for i, player in enumerate(list_data['players'])  
        ) if list_data['players'] else "No players yet") +  
        f"\n\n👁 *Observers:*\n" +  
        ("\n".join(  
            f"{i+1}. 👁 [{obs.split('|')[0]}](tg://user?id={obs.split('|')[1]})"  
            for i, obs in enumerate(list_data['observers'])  
        ) if list_data['observers'] else "No observers yet")  
    )  
    
    return text

async def update_list_messages(list_id, context: ContextTypes.DEFAULT_TYPE):
    active_lists = DataManager.load_data(LISTS_FILE)
    if list_id not in active_lists:
        return

    list_data = active_lists[list_id]  
    list_text = generate_list_text(list_id)  
    is_privileged = AccessControl.is_privileged(int(list_data['creator_id']))  
    
    channels = DataManager.load_data(CHANNELS_FILE)
    for channel_id in channels:
        try:  
            await context.bot.edit_message_text(  
                chat_id=channel_id,  
                message_id=int(list_data['channel_message_id']),  
                text=list_text,  
                reply_markup=KeyboardManager.get_list_keyboard(list_id, is_privileged),  
                parse_mode="Markdown"  
            )  
        except Exception as e:  
            logger.error(f"Error updating list message in channel {channel_id}: {e}")

async def join_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    list_id = query.data.split('_')[1]  
    active_lists = DataManager.load_data(LISTS_FILE)  
    
    if list_id not in active_lists:  
        await query.answer("❌ This list has expired!", show_alert=True)  
        return  
    
    user = update.effective_user  
    user_info = f"{user.full_name}|{user.id}"  
    
    # Check if in observers list  
    for obs in active_lists[list_id]['observers']:  
        if obs.split('|')[1] == str(user.id):  
            await query.answer("❌ You're in observers list and can't join players!", show_alert=True)  
            return  
    
    # Check if already in players list  
    for pl in active_lists[list_id]['players']:  
        if pl.split('|')[1] == str(user.id):  
            await query.answer("⚠️ You're already in players list!", show_alert=True)  
            return  
    
    active_lists[list_id]['players'].append(user_info)  
    DataManager.save_data(LISTS_FILE, active_lists)  
    
    # Save user  
    users = DataManager.load_data(USERS_FILE)  
    users[str(user.id)] = user.full_name  
    DataManager.save_data(USERS_FILE, users)  
    
    await query.answer("✅ Added to players list!", show_alert=True)  
    await update_list_messages(list_id, context)

async def observe_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    list_id = query.data.split('_')[1]  
    active_lists = DataManager.load_data(LISTS_FILE)  
    
    if list_id not in active_lists:  
        await query.answer("❌ This list has expired!", show_alert=True)  
        return  
    
    if not AccessControl.is_privileged(update.effective_user.id):  
        await query.answer("❌ Only admins can observe!", show_alert=True)  
        return  
    
    user = update.effective_user  
    user_info = f"{user.full_name}|{user.id}"  
    
    # Check if in players list  
    for pl in active_lists[list_id]['players']:  
        if pl.split('|')[1] == str(user.id):  
            await query.answer("❌ You're in players list and can't observe!", show_alert=True)  
            return  
    
    # Check if already in observers list  
    for obs in active_lists[list_id]['observers']:  
        if obs.split('|')[1] == str(user.id):  
            await query.answer("⚠️ You're already in observers list!", show_alert=True)  
            return  
    
    if len(active_lists[list_id]['observers']) >= 2:  
        await query.answer("❌ Observers limit reached!", show_alert=True)  
        return  
    
    active_lists[list_id]['observers'].append(user_info)  
    DataManager.save_data(LISTS_FILE, active_lists)  
    await query.answer("✅ Added to observers list!", show_alert=True)  
    await update_list_messages(list_id, context)

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    list_id = query.data.split('_')[1]  
    active_lists = DataManager.load_data(LISTS_FILE)  
    
    if list_id not in active_lists:  
        await query.answer("❌ List not found!", show_alert=True)  
        return  
    
    list_data = active_lists[list_id]  
    user_id = update.effective_user.id  
    
    if str(user_id) != list_data["creator_id"] and not AccessControl.is_privileged(user_id):  
        await query.answer("❌ Only list creator or admins can start the game!", show_alert=True)  
        return  
    
    if len(list_data['players']) < 5:  
        await query.answer("❌ Minimum 5 players required!", show_alert=True)  
        return  
    
    # Mention players  
    player_mentions = "\n".join(  
        f"[{player.split('|')[0]}](tg://user?id={player.split('|')[1]})"  
        for player in list_data['players']  
    )  
    
    observer_mentions = "\n".join(  
        f"👁 [{obs.split('|')[0]}](tg://user?id={obs.split('|')[1]})"  
        for obs in list_data['observers']  
    ) if list_data['observers'] else "No observers"  
    
    # Send game start message to channels  
    channels = DataManager.load_data(CHANNELS_FILE)
    for channel_id in channels:
        try:  
            await context.bot.send_message(  
                chat_id=channel_id,  
                text=(  
                    f"🚀 *Game is starting!*\n\n"  
                    f"🎮 Players:\n{player_mentions}\n\n"  
                    f"👁 Observers:\n{observer_mentions}\n\n"  
                    f"JURASSIC MAFIA GAME"  
                ),  
                parse_mode="Markdown"  
            )  
              
            # Delete the list message  
            await context.bot.delete_message(  
                chat_id=channel_id,  
                message_id=int(list_data['channel_message_id'])  
            )  
        except Exception as e:  
            logger.error(f"Error sending start message to channel {channel_id}: {e}")  
    
    # Remove list from file  
    active_lists.pop(list_id)  
    DataManager.save_data(LISTS_FILE, active_lists)  
    
    await query.answer("✅ Game started successfully!", show_alert=True)

async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    target = query.data.split('_')[2]  
    
    if target == "main":  
        await query.edit_message_text(  
            "🤖 Welcome to Mafia Game List Management Bot!",  
            reply_markup=KeyboardManager.get_main_menu(update.effective_user.id)  
        )  
    elif target == "admin_management":  
        await manage_admins(update, context)  
    elif target == "admin_list":  
        await list_admins(update, context)  
    elif target == "channel_management":  
        await manage_channels(update, context)

async def register_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "channel":
        return

    chat = update.message.chat  
    channels = DataManager.load_data(CHANNELS_FILE)  
    
    if str(chat.id) in channels:  
        return  
        
    channels[str(chat.id)] = {  
        "title": chat.title,  
        "type": chat.type  
    }  
    DataManager.save_data(CHANNELS_FILE, channels)  
    
    owner_msg = (  
        f"🚀 Bot added to new channel:\n"  
        f"🏷 Name: {chat.title}\n"  
        f"🆔 ID: {chat.id}"  
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
            await update.callback_query.answer("❌ An error occurred! Please try again.", show_alert=True)  
        except:  
            pass

def main():
    DataManager.initialize_files()

    app = Application.builder().token(BOT_TOKEN).build()  
    
    # Channel registration  
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, register_channel))  
    
    # Admin management  
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
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_admin_info),  
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_admin)  
            ]  
        },  
        fallbacks=[  
            CallbackQueryHandler(back_handler, pattern="^back_to_")  
        ]  
    )  
    app.add_handler(admin_conv_handler)  
    
    # List management  
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
    
    # Main commands  
    app.add_handler(CommandHandler("start", start))  
    app.add_handler(CallbackQueryHandler(manage_channels, pattern="^manage_channels$"))  
    app.add_handler(CallbackQueryHandler(manage_admins, pattern="^manage_admins$"))  
    app.add_handler(CallbackQueryHandler(list_admins, pattern="^list_admins$"))  
    app.add_handler(CallbackQueryHandler(admin_detail, pattern="^admin_detail_"))  
    app.add_handler(CallbackQueryHandler(remove_admin_action, pattern="^remove_admin_"))  
    app.add_handler(CallbackQueryHandler(leave_channel, pattern="^leave_"))  
    app.add_handler(CallbackQueryHandler(join_list, pattern="^join_"))  
    app.add_handler(CallbackQueryHandler(observe_list, pattern="^observe_"))  
    app.add_handler(CallbackQueryHandler(start_game, pattern="^start_"))  
    app.add_handler(CallbackQueryHandler(back_handler, pattern="^back_to_"))  
    
    # Error handling  
    app.add_error_handler(error_handler)  
    
    # Webhook setup  
    PORT = int(os.environ.get('PORT', 10000))  
    app.run_webhook(  
        listen="0.0.0.0",  
        port=PORT,  
        webhook_url=WEBHOOK_URL  
    )

if __name__ == '__main__':
    main()

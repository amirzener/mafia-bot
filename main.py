import os
import json
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Bot,
    Message,
    Chat,
    User,
)
from telegram.ext import (
    Dispatcher,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext,
)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# File paths
ADMIN_FILE = "admin.json"
CHANNEL_FILE = "channel.json"
GROUP_FILE = "group.json"
ACTIVE_LIST_FILE = "activ_list.json"

# Load JSON data helper functions
def load_json(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# Initialize JSON files if they don't exist
for file in [ADMIN_FILE, CHANNEL_FILE, GROUP_FILE, ACTIVE_LIST_FILE]:
    if not os.path.exists(file):
        save_json(file, {})

# Helper function to check if user is owner
def is_owner(user_id):
    return user_id == OWNER_ID

# Helper function to check if user is admin
def is_admin(user_id):
    admins = load_json(ADMIN_FILE)
    return str(user_id) in admins.keys()

# Helper function to check if user is owner or admin
def is_owner_or_admin(user_id):
    return is_owner(user_id) or is_admin(user_id)

# Handle new chat members (groups/channels)
def handle_new_chat_member(update: Update, context: CallbackContext):
    chat = update.effective_chat
    if chat.type == "channel":
        channels = load_json(CHANNEL_FILE)
        channels[str(chat.id)] = {
            "title": chat.title,
            "username": chat.username,
            "invite_link": chat.invite_link,
            "date_added": datetime.now().isoformat(),
        }
        save_json(CHANNEL_FILE, channels)
        bot.send_message(OWNER_ID, f"✅ Added to channel:\n{chat.title}\nID: {chat.id}")
    elif chat.type in ["group", "supergroup"]:
        groups = load_json(GROUP_FILE)
        groups[str(chat.id)] = {
            "title": chat.title,
            "username": chat.username,
            "invite_link": chat.invite_link,
            "date_added": datetime.now().isoformat(),
        }
        save_json(GROUP_FILE, groups)
        bot.send_message(OWNER_ID, f"✅ Added to group:\n{chat.title}\nID: {chat.id}")

# Command handlers
def menu_command(update: Update, context: CallbackContext):
    if not is_owner(update.effective_user.id):
        return
    
    # Delete the command message
    update.message.delete()
    
    # Show the menu panel
    show_main_menu(update, context)

def list_command(update: Update, context: CallbackContext):
    if not is_owner_or_admin(update.effective_user.id):
        return
    
    update.message.reply_text("⏰ ساعت را به صورت 4 رقمی وارد کنید (مثال: 1930):")
    context.user_data["waiting_for_time"] = True

def handle_text_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    message = update.message
    
    # Check if we're waiting for time input for active list
    if context.user_data.get("waiting_for_time"):
        if not is_owner_or_admin(user_id):
            context.user_data.pop("waiting_for_time", None)
            return
        
        time_str = message.text.strip()
        if len(time_str) == 4 and time_str.isdigit():
            # Create new active list
            active_list = load_json(ACTIVE_LIST_FILE)
            list_id = datetime.now().strftime("%Y%m%d%H%M%S")
            
            active_list[list_id] = {
                "creator": user_id,
                "time": time_str,
                "players": [],
                "observers": [],
                "created_at": datetime.now().isoformat(),
            }
            save_json(ACTIVE_LIST_FILE, active_list)
            
            # Send message to channels
            channels = load_json(CHANNEL_FILE)
            for channel_id in channels:
                try:
                    keyboard = [
                        [
                            InlineKeyboardButton("هستم", callback_data=f"join_player:{list_id}"),
                            InlineKeyboardButton("ناظر", callback_data=f"join_observer:{list_id}"),
                            InlineKeyboardButton("شروع", callback_data=f"start_game:{list_id}"),
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    sent_msg = bot.send_message(
                        chat_id=channel_id,
                        text=f"🎮 جهت ثبت نام در بازی در ساعت {time_str} اعلام حضور کنید:",
                        reply_markup=reply_markup,
                    )
                    
                    # Save message ID for later updates
                    active_list[list_id]["channel_message_id"] = sent_msg.message_id
                    active_list[list_id]["channel_id"] = channel_id
                    save_json(ACTIVE_LIST_FILE, active_list)
                except Exception as e:
                    print(f"Failed to send message to channel {channel_id}: {e}")
            
            message.reply_text(f"✅ لیست بازی برای ساعت {time_str} ایجاد شد.")
        else:
            message.reply_text("⚠️ لطفا ساعت را به صورت 4 رقمی وارد کنید (مثال: 1930).")
        
        context.user_data.pop("waiting_for_time", None)

# Menu panel functions
def show_main_menu(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📋 نمایش لیست گروه ها", callback_data="show_groups")],
        [InlineKeyboardButton("📢 نمایش لیست کانال ها", callback_data="show_channels")],
        [InlineKeyboardButton("👤 نمایش لیست ادمین ها", callback_data="show_admins")],
        [InlineKeyboardButton("❌ بستن پنل", callback_data="close_panel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        update.callback_query.edit_message_text(
            text="🔹 پنل مدیریت ربات 🔹",
            reply_markup=reply_markup,
        )
    else:
        update.message.reply_text(
            text="🔹 پنل مدیریت ربات 🔹",
            reply_markup=reply_markup,
        )

def show_groups_menu(update: Update, context: CallbackContext):
    groups = load_json(GROUP_FILE)
    keyboard = []
    
    for group_id, group_info in groups.items():
        keyboard.append([
            InlineKeyboardButton(
                f"🚫 {group_info['title']}",
                callback_data=f"leave_chat:{group_id}:group",
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        text="📋 لیست گروه ها:",
        reply_markup=reply_markup,
    )

def show_channels_menu(update: Update, context: CallbackContext):
    channels = load_json(CHANNEL_FILE)
    keyboard = []
    
    for channel_id, channel_info in channels.items():
        keyboard.append([
            InlineKeyboardButton(
                f"🚫 {channel_info['title']}",
                callback_data=f"leave_chat:{channel_id}:channel",
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        text="📢 لیست کانال ها:",
        reply_markup=reply_markup,
    )

def show_admins_list(update: Update, context: CallbackContext):
    admins = load_json(ADMIN_FILE)
    admin_list = "\n".join(
        f"👤 {info['alias']} - `{admin_id}`"
        for admin_id, info in admins.items()
    )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        text=f"👥 لیست ادمین ها:\n\n{admin_list}",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

# Callback query handlers
def handle_callback_query(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_owner(user_id):
        query.answer("⛔ شما مجاز به استفاده از این پنل نیستید.")
        return
    
    data = query.data
    
    if data == "show_groups":
        show_groups_menu(update, context)
    elif data == "show_channels":
        show_channels_menu(update, context)
    elif data == "show_admins":
        show_admins_list(update, context)
    elif data == "back_to_main":
        show_main_menu(update, context)
    elif data == "close_panel":
        query.delete_message()
    elif data.startswith("leave_chat:"):
        _, chat_id, chat_type = data.split(":")
        try:
            bot.leave_chat(chat_id=int(chat_id))
            
            if chat_type == "group":
                groups = load_json(GROUP_FILE)
                groups.pop(chat_id, None)
                save_json(GROUP_FILE, groups)
            else:
                channels = load_json(CHANNEL_FILE)
                channels.pop(chat_id, None)
                save_json(CHANNEL_FILE, channels)
            
            query.answer(f"✅ از {chat_type} خارج شد.")
            if chat_type == "group":
                show_groups_menu(update, context)
            else:
                show_channels_menu(update, context)
        except Exception as e:
            query.answer(f"❌ خطا در خارج شدن: {str(e)}")
    elif data.startswith(("join_player:", "join_observer:", "start_game:")):
        handle_game_actions(update, context)

def handle_game_actions(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    action, list_id = data.split(":")
    active_list = load_json(ACTIVE_LIST_FILE)
    list_data = active_list.get(list_id)
    
    if not list_data:
        query.answer("❌ این لیست منقضی شده است.")
        return
    
    if action == "join_player":
        # Any user can join as player
        if user_id not in list_data["players"]:
            list_data["players"].append(user_id)
            active_list[list_id] = list_data
            save_json(ACTIVE_LIST_FILE, active_list)
            query.answer("✅ شما به عنوان بازیکن ثبت نام کردید.")
        else:
            query.answer("⚠️ شما قبلا ثبت نام کرده اید.")
        
        update_active_list_message(list_id)
    
    elif action == "join_observer":
        # Only owner/admins can join as observer
        if not is_owner_or_admin(user_id):
            query.answer("⛔ فقط ادمین ها می‌توانند ناظر باشند.")
            return
        
        if len(list_data["observers"]) >= 2:
            query.answer("⚠️ حد مجاز ناظرین (2 نفر) تکمیل شده است.")
            return
        
        if user_id not in list_data["observers"]:
            list_data["observers"].append(user_id)
            active_list[list_id] = list_data
            save_json(ACTIVE_LIST_FILE, active_list)
            query.answer("✅ شما به عنوان ناظر ثبت نام کردید.")
        else:
            query.answer("⚠️ شما قبلا به عنوان ناظر ثبت نام کرده اید.")
        
        update_active_list_message(list_id)
    
    elif action == "start_game":
        # Only owner/admins can start the game
        if not is_owner_or_admin(user_id):
            query.answer("⛔ فقط ادمین ها می‌توانند بازی را شروع کنند.")
            return
        
        # Notify players in groups
        groups = load_json(GROUP_FILE)
        for group_id in groups:
            try:
                # Tag players in batches of 5
                players = list_data["players"]
                for i in range(0, len(players), 5):
                    batch = players[i:i+5]
                    mentions = " ".join(f"<a href='tg://user?id={p}'>.</a>" for p in batch)
                    bot.send_message(
                        chat_id=group_id,
                        text=f"🎮 دوستان عزیز لابی زده شد تشریف بیارید:\n{mentions}",
                        parse_mode="HTML",
                    )
            except Exception as e:
                print(f"Failed to notify group {group_id}: {e}")
        
        # Delete the channel message and send final notification
        try:
            bot.delete_message(
                chat_id=list_data["channel_id"],
                message_id=list_data["channel_message_id"],
            )
            bot.send_message(
                chat_id=list_data["channel_id"],
                text="🎮 دوستان عزیز لابی زده شد تشریف بیارید",
            )
        except Exception as e:
            print(f"Failed to update channel message: {e}")
        
        # Clear the active list
        active_list.pop(list_id, None)
        save_json(ACTIVE_LIST_FILE, active_list)
        query.answer("✅ بازی شروع شد!")

def update_active_list_message(list_id):
    active_list = load_json(ACTIVE_LIST_FILE)
    list_data = active_list.get(list_id)
    
    if not list_data or "channel_id" not in list_data:
        return
    
    # Prepare players list
    players_text = ""
    if list_data["players"]:
        players_text = "\n".join(
            f"{i+1}. <a href='tg://user?id={p}'>بازیکن {i+1}</a>"
            for i, p in enumerate(list_data["players"])
        )
    else:
        players_text = "هنوز بازیکنی ثبت نام نکرده است."
    
    # Prepare observers list
    observers_text = ""
    admins = load_json(ADMIN_FILE)
    if list_data["observers"]:
        observers_text = "\n".join(
            f"👁️ {admins.get(str(o), {}).get('alias', f'ناظر {i+1}')}"
            for i, o in enumerate(list_data["observers"])
        )
    else:
        observers_text = "هنوز ناظری ثبت نام نکرده است."
    
    message_text = (
        f"🎮 لیست بازی ساعت {list_data['time']}\n\n"
        f"🔹 بازیکنان:\n{players_text}\n\n"
        f"🔹 ناظران:\n{observers_text}"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("هستم", callback_data=f"join_player:{list_id}"),
            InlineKeyboardButton("ناظر", callback_data=f"join_observer:{list_id}"),
            InlineKeyboardButton("شروع", callback_data=f"start_game:{list_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        bot.edit_message_text(
            chat_id=list_data["channel_id"],
            message_id=list_data["channel_message_id"],
            text=message_text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    except Exception as e:
        print(f"Failed to update active list message: {e}")

# Set up handlers
dispatcher.add_handler(CommandHandler("menu", menu_command))
dispatcher.add_handler(CommandHandler("list", list_command))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text_message))
dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))

# Handle new chat members (for when bot is added to groups/channels)
def handle_chat_member_update(update: Update, context: CallbackContext):
    if update.chat_member.new_chat_member.user.id == bot.id:
        handle_new_chat_member(update, context)

dispatcher.add_handler(MessageHandler(Filters.status_update, handle_chat_member_update))

# Flask route for webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return jsonify({'status': 'ok'})

# Set webhook
def set_webhook():
    bot.set_webhook(url=WEBHOOK_URL)

if __name__ == '__main__':
    set_webhook()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

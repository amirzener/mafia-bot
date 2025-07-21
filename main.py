import os
import json
from datetime import datetime
from dotenv import load_dotenv
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
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# بارگذاری متغیرهای محیطی


# پیکربندی ربات (مستقیماً از محیط می‌خواند):
BOT_TOKEN = os.environ.get('BOT_TOKEN')  # دقت کنید به حروف بزرگ/کوچک حساس است
OWNER_ID = int(os.environ.get('OWNER_ID'))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

# ایجاد برنامه ربات
application = Application.builder().token(BOT_TOKEN).build()

# مسیر فایل‌های JSON
ADMIN_FILE = "admin.json"
CHANNEL_FILE = "channel.json"
GROUP_FILE = "group.json"
ACTIVE_LIST_FILE = "activ_list.json"

# توابع کمکی برای مدیریت فایل‌های JSON
def load_json(file_path):
    try:
        with open(file_path, "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json(file_path, data):
    with open(file_path, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ایجاد فایل‌های JSON در صورت عدم وجود
for file in [ADMIN_FILE, CHANNEL_FILE, GROUP_FILE, ACTIVE_LIST_FILE]:
    if not os.path.exists(file):
        save_json(file, {})

# توابع کمکی برای بررسی دسترسی
def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    admins = load_json(ADMIN_FILE)
    return str(user_id) in admins.keys()

def is_owner_or_admin(user_id):
    return is_owner(user_id) or is_admin(user_id)

# مدیریت اضافه شدن به گروه/کانال جدید
async def handle_new_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    
    # بررسی اینکه آیا ربات به چت اضافه شده است
    if user and user.id == context.bot.id:
        if chat.type == "channel":
            channels = load_json(CHANNEL_FILE)
            channels[str(chat.id)] = {
                "title": chat.title,
                "username": chat.username,
                "invite_link": chat.invite_link,
                "date_added": datetime.now().isoformat(),
            }
            save_json(CHANNEL_FILE, channels)
            await context.bot.send_message(
                OWNER_ID,
                f"✅ ربات به کانال اضافه شد:\n\n🏷 نام: {chat.title}\n🆔 شناسه: {chat.id}\n👤 یوزرنیم: @{chat.username if chat.username else 'ندارد'}"
            )
        elif chat.type in ["group", "supergroup"]:
            groups = load_json(GROUP_FILE)
            groups[str(chat.id)] = {
                "title": chat.title,
                "username": chat.username,
                "invite_link": chat.invite_link,
                "date_added": datetime.now().isoformat(),
            }
            save_json(GROUP_FILE, groups)
            await context.bot.send_message(
                OWNER_ID,
                f"✅ ربات به گروه اضافه شد:\n\n🏷 نام: {chat.title}\n🆔 شناسه: {chat.id}\n👤 یوزرنیم: @{chat.username if chat.username else 'ندارد'}\n{'👥 سوپرگروه' if chat.type == 'supergroup' else '👥 گروه معمولی'}"
            )

# دستورات ربات
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    # حذف پیام دستور
    await update.message.delete()

    # نمایش منوی اصلی
    await show_main_menu(update, context)

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner_or_admin(update.effective_user.id):
        return

    await update.message.reply_text("⏰ ساعت را به صورت 4 رقمی وارد کنید (مثال: 1930):")
    context.user_data["waiting_for_time"] = True

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message

    # بررسی انتظار برای دریافت زمان
    if context.user_data.get("waiting_for_time"):
        if not is_owner_or_admin(user_id):
            context.user_data.pop("waiting_for_time", None)
            return

        time_str = message.text.strip()    
        if len(time_str) == 4 and time_str.isdigit():    
            # ایجاد لیست فعال جدید    
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
                
            # ارسال پیام به کانال‌ها    
            channels = load_json(CHANNEL_FILE)    
            for channel_id in channels:    
                try:    
                    keyboard = [    
                        [InlineKeyboardButton("🎮 هستم", callback_data=f"join_player:{list_id}")],
                        [InlineKeyboardButton("👁️ ناظر", callback_data=f"join_observer:{list_id}")],
                        [InlineKeyboardButton("🚀 شروع", callback_data=f"start_game:{list_id}")],
                    ]    
                    reply_markup = InlineKeyboardMarkup(keyboard)    
                        
                    sent_msg = await context.bot.send_message(    
                        chat_id=channel_id,    
                        text=f"🎮 جهت ثبت نام در بازی در ساعت {time_str} اعلام حضور کنید:",    
                        reply_markup=reply_markup,    
                    )    
                        
                    # ذخیره اطلاعات پیام برای به‌روزرسانی‌های بعدی    
                    active_list[list_id]["channel_message_id"] = sent_msg.message_id    
                    active_list[list_id]["channel_id"] = channel_id    
                    save_json(ACTIVE_LIST_FILE, active_list)    
                except Exception as e:    
                    print(f"خطا در ارسال پیام به کانال {channel_id}: {e}")    
            
            await message.reply_text(f"✅ لیست بازی برای ساعت {time_str} ایجاد شد.")    
        else:    
            await message.reply_text("⚠️ لطفا ساعت را به صورت 4 رقمی وارد کنید (مثال: 1930).")    
        
        context.user_data.pop("waiting_for_time", None)

# توابع منو
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 نمایش لیست گروه ها", callback_data="show_groups")],
        [InlineKeyboardButton("📢 نمایش لیست کانال ها", callback_data="show_channels")],
        [InlineKeyboardButton("👤 نمایش لیست ادمین ها", callback_data="show_admins")],
        [InlineKeyboardButton("❌ بستن پنل", callback_data="close_panel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text="🔹 پنل مدیریت ربات 🔹",
            reply_markup=reply_markup,
        )
    else:
        await update.message.reply_text(
            text="🔹 پنل مدیریت ربات 🔹",
            reply_markup=reply_markup,
        )

async def show_groups_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    await update.callback_query.edit_message_text(
        text="📋 لیست گروه ها:",
        reply_markup=reply_markup,
    )

async def show_channels_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    await update.callback_query.edit_message_text(
        text="📢 لیست کانال ها:",
        reply_markup=reply_markup,
    )

async def show_admins_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = load_json(ADMIN_FILE)
    admin_list = "\n".join(
        f"👤 {info['alias']} - {admin_id}"
        for admin_id, info in admins.items()
    )

    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        text=f"👥 لیست ادمین ها:\n\n{admin_list}",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

# مدیریت رویدادهای دکمه‌ها
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_owner(user_id):
        await query.answer("⛔ شما مجاز به استفاده از این پنل نیستید.")
        return

    data = query.data

    if data == "show_groups":
        await show_groups_menu(update, context)
    elif data == "show_channels":
        await show_channels_menu(update, context)
    elif data == "show_admins":
        await show_admins_list(update, context)
    elif data == "back_to_main":
        await show_main_menu(update, context)
    elif data == "close_panel":
        await query.delete_message()
    elif data.startswith("leave_chat:"):
        _, chat_id, chat_type = data.split(":")
        try:
            await context.bot.leave_chat(chat_id=int(chat_id))

            if chat_type == "group":    
                groups = load_json(GROUP_FILE)    
                groups.pop(chat_id, None)    
                save_json(GROUP_FILE, groups)    
            else:    
                channels = load_json(CHANNEL_FILE)    
                channels.pop(chat_id, None)    
                save_json(CHANNEL_FILE, channels)    
                
            await query.answer(f"✅ از {chat_type} خارج شد.")    
            if chat_type == "group":    
                await show_groups_menu(update, context)    
            else:    
                await show_channels_menu(update, context)    
        except Exception as e:    
            await query.answer(f"❌ خطا در خارج شدن: {str(e)}")

    elif data.startswith(("join_player:", "join_observer:", "start_game:")):
        await handle_game_actions(update, context)

async def handle_game_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    action, list_id = data.split(":")
    active_list = load_json(ACTIVE_LIST_FILE)
    list_data = active_list.get(list_id)

    if not list_data:
        await query.answer("❌ این لیست منقضی شده است.")
        return

    if action == "join_player":
        # هر کاربری می‌تواند به عنوان بازیکن ثبت نام کند
        if user_id not in list_data["players"]:
            list_data["players"].append(user_id)
            active_list[list_id] = list_data
            save_json(ACTIVE_LIST_FILE, active_list)
            await query.answer("✅ شما به عنوان بازیکن ثبت نام کردید.")
        else:
            await query.answer("⚠️ شما قبلا ثبت نام کرده اید.")

        await update_active_list_message(list_id, context)

    elif action == "join_observer":
        # فقط مالک و ادمین‌ها می‌توانند ناظر باشند
        if not is_owner_or_admin(user_id):
            await query.answer("⛔ فقط ادمین ها می‌توانند ناظر باشند.")
            return

        if len(list_data["observers"]) >= 2:    
            await query.answer("⚠️ حد مجاز ناظرین (2 نفر) تکمیل شده است.")    
            return    
            
        if user_id not in list_data["observers"]:    
            list_data["observers"].append(user_id)    
            active_list[list_id] = list_data    
            save_json(ACTIVE_LIST_FILE, active_list)    
            await query.answer("✅ شما به عنوان ناظر ثبت نام کردید.")    
        else:    
            await query.answer("⚠️ شما قبلا به عنوان ناظر ثبت نام کرده اید.")    
            
        await update_active_list_message(list_id, context)

    elif action == "start_game":
        # فقط مالک و ادمین‌ها می‌توانند بازی را شروع کنند
        if not is_owner_or_admin(user_id):
            await query.answer("⛔ فقط ادمین ها می‌توانند بازی را شروع کنند.")
            return

        # اطلاع‌رسانی به بازیکنان در گروه‌ها    
        groups = load_json(GROUP_FILE)    
        for group_id in groups:    
            try:    
                # تگ کردن بازیکنان در دسته‌های 5 نفره    
                players = list_data["players"]    
                for i in range(0, len(players), 5):    
                    batch = players[i:i+5]    
                    mentions = " ".join(f"<a href='tg://user?id={p}'>.</a>" for p in batch)    
                    await context.bot.send_message(    
                        chat_id=group_id,    
                        text=mentions,    
                        parse_mode="HTML",    
                    )    
            except Exception as e:    
                print(f"خطا در اطلاع‌رسانی به گروه {group_id}: {e}")    
            
        # حذف پیام لیست و ارسال پیام نهایی    
        try:    
            await context.bot.delete_message(    
                chat_id=list_data["channel_id"],    
                message_id=list_data["channel_message_id"],    
            )    
            await context.bot.send_message(    
                chat_id=list_data["channel_id"],    
                text="دوستان عزیز لابی زده شد تشریف بیارید",    
            )    
        except Exception as e:    
            print(f"خطا در به‌روزرسانی پیام کانال: {e}")    
            
        # پاک کردن لیست فعال    
        active_list.pop(list_id, None)    
        save_json(ACTIVE_LIST_FILE, active_list)    
        await query.answer("✅ بازی شروع شد!")

async def update_active_list_message(list_id, context: ContextTypes.DEFAULT_TYPE):
    active_list = load_json(ACTIVE_LIST_FILE)
    list_data = active_list.get(list_id)

    if not list_data or "channel_id" not in list_data:
        return

    # آماده‌سازی لیست بازیکنان
    players_text = ""
    if list_data["players"]:
        players_text = "\n".join(
            f"{i+1}. [{user.first_name}](tg://user?id={user_id})"
            for i, user_id in enumerate(list_data["players"])
        )
    else:
        players_text = "هنوز بازیکنی ثبت نام نکرده است."

    # آماده‌سازی لیست ناظران
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
        [InlineKeyboardButton("🎮 هستم", callback_data=f"join_player:{list_id}")],
        [InlineKeyboardButton("👁️ ناظر", callback_data=f"join_observer:{list_id}")],
        [InlineKeyboardButton("🚀 شروع", callback_data=f"start_game:{list_id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.edit_message_text(
            chat_id=list_data["channel_id"],
            message_id=list_data["channel_message_id"],
            text=message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"خطا در به‌روزرسانی لیست فعال: {e}")

# مدیریت عضویت جدید در چت
async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.chat_member and update.chat_member.new_chat_member.user.id == context.bot.id:
        await handle_new_chat_member(update, context)

# تنظیم هندلرها
application.add_handler(CommandHandler("menu", menu_command))
application.add_handler(CommandHandler("list", list_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
application.add_handler(CallbackQueryHandler(handle_callback_query))
application.add_handler(MessageHandler(filters.StatusUpdate.ALL, handle_chat_member_update))

if __name__ == "__main__":
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=WEBHOOK_URL
)

import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    CallbackContext
)
from flask import Flask, request, jsonify

# تنظیمات اولیه
API_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
# بارگذاری داده‌ها
def load_data():
    try:
        with open('data.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # اگر فایل وجود نداشت یا خراب بود، یک ساختار پیش‌فرض ایجاد می‌کنیم
        default_data = {
            "owner": None,
            "senior_admins": [],
            "normal_admins": [],
            "chats": []
        }
        with open('data.json', 'w') as f:
            json.dump(default_data, f, indent=4)
        return default_data

# ذخیره داده‌ها
def save_data(data):
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4)

# بررسی سطح دسترسی کاربر
def check_access(user_id, required_level):
    data = load_data()
    
    if required_level == "owner":
        return user_id == data.get("owner")
    elif required_level == "senior_admin":
        return user_id in data.get("senior_admins", []) or user_id == data.get("owner")
    elif required_level == "normal_admin":
        return user_id in data.get("normal_admins", []) or user_id in data.get("senior_admins", []) or user_id == data.get("owner")
    return False

# ایجاد منوی مالک
def create_owner_menu():
    keyboard = [
        [InlineKeyboardButton("مدیریت مدیران ارشد", callback_data='manage_senior')],
        [InlineKeyboardButton("مدیریت مدیران معمولی", callback_data='manage_normal')],
        [InlineKeyboardButton("لیست مقام داران", callback_data='list_admins')],
        [InlineKeyboardButton("لیست کانال‌ها و گروه‌ها", callback_data='list_chats')],
        [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ایجاد منوی مدیر ارشد
def create_senior_menu():
    keyboard = [
        [InlineKeyboardButton("مدیریت مدیران معمولی", callback_data='manage_normal')],
        [InlineKeyboardButton("لیست مقام داران", callback_data='list_admins')],
        [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

# مدیریت مدیران ارشد
async def manage_senior_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("افزودن مدیر ارشد", callback_data='add_senior')],
        [InlineKeyboardButton("حذف مدیر ارشد", callback_data='remove_senior')],
        [InlineKeyboardButton("بازگشت", callback_data='back_to_main')],
        [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="پنل مدیریت مدیران ارشد:",
        reply_markup=reply_markup
    )

# مدیریت مدیران معمولی
async def manage_normal_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("افزودن مدیر معمولی", callback_data='add_normal')],
        [InlineKeyboardButton("حذف مدیر معمولی", callback_data='remove_normal')],
        [InlineKeyboardButton("بازگشت", callback_data='back_to_main')],
        [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="پنل مدیریت مدیران معمولی:",
        reply_markup=reply_markup
    )

# لیست مقام داران
async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = load_data()
    owner_id = data.get("owner")
    senior_admins = data.get("senior_admins", [])
    normal_admins = data.get("normal_admins", [])
    
    text = "لیست مقام داران:\n\n"
    text += f"👑 مالک: {owner_id}\n\n"
    text += "🔴 مدیران ارشد:\n"
    text += "\n".join([f"• {admin}" for admin in senior_admins]) + "\n\n"
    text += "🔵 مدیران معمولی:\n"
    text += "\n".join([f"• {admin}" for admin in normal_admins])
    
    keyboard = [
        [InlineKeyboardButton("بازگشت", callback_data='back_to_main')],
        [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup
    )

# لیست کانال‌ها و گروه‌ها
async def list_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = load_data()
    chats = data.get("chats", [])
    
    if not chats:
        text = "ربات در هیچ کانال یا گروهی عضو نیست."
    else:
        text = "لیست کانال‌ها و گروه‌ها:\n\n"
        for chat in chats:
            text += f"• {chat.get('title', 'بدون نام')} (ID: {chat.get('id')}) - نوع: {chat.get('type')}\n"
    
    keyboard = []
    for chat in chats:
        keyboard.append([InlineKeyboardButton(
            f"خروج از {chat.get('title', chat.get('id'))}",
            callback_data=f"leave_chat_{chat.get('id')}"
        )])
    
    keyboard.append([InlineKeyboardButton("بازگشت", callback_data='back_to_main')])
    keyboard.append([InlineKeyboardButton("بستن پنل", callback_data='close_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup
    )

# خروج از چت
async def leave_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = int(query.data.split('_')[-1])
    data = load_data()
    
    # حذف چت از لیست
    data["chats"] = [chat for chat in data.get("chats", []) if chat.get("id") != chat_id]
    save_data(data)
    
    # تلاش برای خروج از چت
    try:
        await context.bot.leave_chat(chat_id=chat_id)
        text = f"✅ ربات با موفقیت از چت با ID {chat_id} خارج شد."
    except Exception as e:
        text = f"❌ خطا در خروج از چت: {str(e)}"
    
    keyboard = [
        [InlineKeyboardButton("بازگشت به لیست چت‌ها", callback_data='list_chats')],
        [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup
    )

# بستن پنل
async def close_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="پنل مدیریت بسته شد."
    )

# بازگشت به منوی اصلی
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = load_data()
    
    if user_id == data.get("owner"):
        reply_markup = create_owner_menu()
        text = "پنل مدیریت مالک:"
    elif user_id in data.get("senior_admins", []):
        reply_markup = create_senior_menu()
        text = "پنل مدیریت مدیر ارشد:"
    else:
        return
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup
    )

# افزودن مدیر ارشد
async def add_senior_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="لطفاً شناسه عددی کاربر را برای افزودن به مدیران ارشد ارسال کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("بازگشت", callback_data='manage_senior')],
            [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
        ])
    )
    
    return "waiting_for_senior_id"

# ذخیره مدیر ارشد جدید
async def save_senior_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = load_data()
    
    if not check_access(user_id, "owner"):
        await update.message.reply_text("شما دسترسی لازم برای این عمل را ندارید.")
        return
    
    try:
        new_senior_id = int(update.message.text)
        if new_senior_id in data["senior_admins"]:
            await update.message.reply_text("این کاربر قبلاً به عنوان مدیر ارشد اضافه شده است.")
        else:
            data["senior_admins"].append(new_senior_id)
            save_data(data)
            await update.message.reply_text(f"کاربر با شناسه {new_senior_id} به مدیران ارشد اضافه شد.")
    except ValueError:
        await update.message.reply_text("شناسه کاربر باید یک عدد باشد.")
    
    return -1

# حذف مدیر ارشد
async def remove_senior_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = load_data()
    senior_admins = data.get("senior_admins", [])
    
    if not senior_admins:
        await query.edit_message_text(
            text="هیچ مدیر ارشدی برای حذف وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("بازگشت", callback_data='manage_senior')],
                [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
            ])
        )
        return
    
    keyboard = []
    for admin in senior_admins:
        keyboard.append([InlineKeyboardButton(
            f"حذف مدیر ارشد {admin}",
            callback_data=f"confirm_remove_senior_{admin}"
        )])
    
    keyboard.append([InlineKeyboardButton("بازگشت", callback_data='manage_senior')])
    keyboard.append([InlineKeyboardButton("بستن پنل", callback_data='close_panel')])
    
    await query.edit_message_text(
        text="لیست مدیران ارشد برای حذف:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# تأیید حذف مدیر ارشد
async def confirm_remove_senior(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    admin_id = int(query.data.split('_')[-1])
    
    keyboard = [
        [InlineKeyboardButton("✅ تأیید حذف", callback_data=f"do_remove_senior_{admin_id}")],
        [InlineKeyboardButton("❌ انصراف", callback_data='remove_senior')],
        [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
    ]
    
    await query.edit_message_text(
        text=f"آیا از حذف مدیر ارشد با شناسه {admin_id} مطمئن هستید؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# اجرای حذف مدیر ارشد
async def do_remove_senior(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    admin_id = int(query.data.split('_')[-1])
    data = load_data()
    
    if admin_id in data["senior_admins"]:
        data["senior_admins"].remove(admin_id)
        save_data(data)
        text = f"مدیر ارشد با شناسه {admin_id} با موفقیت حذف شد."
    else:
        text = "مدیر ارشد مورد نظر یافت نشد."
    
    keyboard = [
        [InlineKeyboardButton("بازگشت به مدیریت مدیران ارشد", callback_data='manage_senior')],
        [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
    ]
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# افزودن مدیر معمولی
async def add_normal_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="لطفاً شناسه عددی کاربر را برای افزودن به مدیران معمولی ارسال کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("بازگشت", callback_data='manage_normal')],
            [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
        ])
    )
    
    return "waiting_for_normal_id"

# ذخیره مدیر معمولی جدید
async def save_normal_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = load_data()
    
    if not (check_access(user_id, "owner") or check_access(user_id, "senior_admin")):
        await update.message.reply_text("شما دسترسی لازم برای این عمل را ندارید.")
        return
    
    try:
        new_normal_id = int(update.message.text)
        if new_normal_id in data["normal_admins"]:
            await update.message.reply_text("این کاربر قبلاً به عنوان مدیر معمولی اضافه شده است.")
        else:
            data["normal_admins"].append(new_normal_id)
            save_data(data)
            await update.message.reply_text(f"کاربر با شناسه {new_normal_id} به مدیران معمولی اضافه شد.")
    except ValueError:
        await update.message.reply_text("شناسه کاربر باید یک عدد باشد.")
    
    return -1

# حذف مدیر معمولی
async def remove_normal_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = load_data()
    normal_admins = data.get("normal_admins", [])
    
    if not normal_admins:
        await query.edit_message_text(
            text="هیچ مدیر معمولی برای حذف وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("بازگشت", callback_data='manage_normal')],
                [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
            ])
        )
        return
    
    keyboard = []
    for admin in normal_admins:
        keyboard.append([InlineKeyboardButton(
            f"حذف مدیر معمولی {admin}",
            callback_data=f"confirm_remove_normal_{admin}"
        )])
    
    keyboard.append([InlineKeyboardButton("بازگشت", callback_data='manage_normal')])
    keyboard.append([InlineKeyboardButton("بستن پنل", callback_data='close_panel')])
    
    await query.edit_message_text(
        text="لیست مدیران معمولی برای حذف:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# تأیید حذف مدیر معمولی
async def confirm_remove_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    admin_id = int(query.data.split('_')[-1])
    
    keyboard = [
        [InlineKeyboardButton("✅ تأیید حذف", callback_data=f"do_remove_normal_{admin_id}")],
        [InlineKeyboardButton("❌ انصراف", callback_data='remove_normal')],
        [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
    ]
    
    await query.edit_message_text(
        text=f"آیا از حذف مدیر معمولی با شناسه {admin_id} مطمئن هستید؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# اجرای حذف مدیر معمولی
async def do_remove_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    admin_id = int(query.data.split('_')[-1])
    data = load_data()
    
    if admin_id in data["normal_admins"]:
        data["normal_admins"].remove(admin_id)
        save_data(data)
        text = f"مدیر معمولی با شناسه {admin_id} با موفقیت حذف شد."
    else:
        text = "مدیر معمولی مورد نظر یافت نشد."
    
    keyboard = [
        [InlineKeyboardButton("بازگشت به مدیریت مدیران معمولی", callback_data='manage_normal')],
        [InlineKeyboardButton("بستن پنل", callback_data='close_panel')]
    ]
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ست کردن مدیر معمولی با ریپلی
async def set_normal_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = load_data()
    
    if not check_access(user_id, "senior_admin"):
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("لطفاً این دستور را روی پیام کاربر مورد نظر ریپلی کنید.")
        return
    
    if update.message.text.lower() != "ست":
        return
    
    target_user = update.message.reply_to_message.from_user
    target_id = target_user.id
    
    if target_id in data["normal_admins"]:
        await update.message.reply_text("این کاربر قبلاً به عنوان مدیر معمولی تنظیم شده است.")
        return
    
    data["normal_admins"].append(target_id)
    save_data(data)
    
    await update.message.reply_text(
        f"کاربر {target_user.full_name} (@{target_user.username or 'بدون یوزرنیم'}) به مدیران معمولی اضافه شد."
    )

# باز کردن پنل مدیریت
async def open_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = load_data()
    
    if update.message.text.lower() != "منو":
        return
    
    if user_id == data.get("owner"):
        reply_markup = create_owner_menu()
        text = "پنل مدیریت مالک:"
    elif user_id in data.get("senior_admins", []):
        reply_markup = create_senior_menu()
        text = "پنل مدیریت مدیر ارشد:"
    else:
        return
    
    await update.message.reply_text(
        text=text,
        reply_markup=reply_markup
    )

# ذخیره اطلاعات چت‌ها
async def save_chat_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.my_chat_member.chat if update.my_chat_member else update.message.chat
    data = load_data()
    
    chat_info = {
        "id": chat.id,
        "title": getattr(chat, 'title', None),
        "type": chat.type,
        "username": getattr(chat, 'username', None)
    }
    
    # اگر چت جدید است یا اطلاعاتش تغییر کرده، ذخیره می‌کنیم
    existing_chat = next((c for c in data["chats"] if c["id"] == chat.id), None)
    if not existing_chat or existing_chat != chat_info:
        if existing_chat:
            data["chats"].remove(existing_chat)
        data["chats"].append(chat_info)
        save_data(data)

# حذف اطلاعات چت هنگام خروج
async def remove_chat_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.my_chat_member.chat
    data = load_data()
    
    data["chats"] = [c for c in data["chats"] if c["id"] != chat.id]
    save_data(data)

# تنظیم مالک اولیه
async def set_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    
    if data.get("owner") is not None:
        return
    
    data["owner"] = update.message.from_user.id
    save_data(data)
    
    await update.message.reply_text(
        "شما به عنوان مالک ربات تنظیم شدید. از این پس می‌توانید از پنل مدیریت استفاده کنید."
    )

# هندلرهای اصلی
def main():
    # بارگذاری داده‌ها و تنظیم مالک
    data = load_data()
    global OWNER_ID
    OWNER_ID = data.get("owner")
    
    # ایجاد برنامه
    application = Application.builder().token(TOKEN).build()
    
    # افزودن هندلرهای دستورات
    application.add_handler(CommandHandler("start", set_owner))
    
    # افزودن هندلرهای پیام‌ها
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), open_panel))
    application.add_handler(MessageHandler(filters.TEXT & filters.REPLY, set_normal_admin_reply))
    
    # افزودن هندلرهای callback
    application.add_handler(CallbackQueryHandler(manage_senior_admins, pattern='^manage_senior$'))
    application.add_handler(CallbackQueryHandler(manage_normal_admins, pattern='^manage_normal$'))
    application.add_handler(CallbackQueryHandler(list_admins, pattern='^list_admins$'))
    application.add_handler(CallbackQueryHandler(list_chats, pattern='^list_chats$'))
    application.add_handler(CallbackQueryHandler(leave_chat, pattern='^leave_chat_'))
    application.add_handler(CallbackQueryHandler(close_panel, pattern='^close_panel$'))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern='^back_to_main$'))
    
    application.add_handler(CallbackQueryHandler(add_senior_admin, pattern='^add_senior$'))
    application.add_handler(CallbackQueryHandler(remove_senior_admin, pattern='^remove_senior$'))
    application.add_handler(CallbackQueryHandler(confirm_remove_senior, pattern='^confirm_remove_senior_'))
    application.add_handler(CallbackQueryHandler(do_remove_senior, pattern='^do_remove_senior_'))
    
    application.add_handler(CallbackQueryHandler(add_normal_admin, pattern='^add_normal$'))
    application.add_handler(CallbackQueryHandler(remove_normal_admin, pattern='^remove_normal$'))
    application.add_handler(CallbackQueryHandler(confirm_remove_normal, pattern='^confirm_remove_normal_'))
    application.add_handler(CallbackQueryHandler(do_remove_normal, pattern='^do_remove_normal_'))
    
    # هندلرهای حالت‌ها
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), save_senior_admin), group=1)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), save_normal_admin), group=2)
    
    # هندلرهای عضویت در چت‌ها
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL | filters.ChatType.GROUP | filters.ChatType.SUPERGROUP, save_chat_info))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, remove_chat_info))
    
    # راه‌اندازی وب‌هوک
    app = Flask(__name__)
    
    @app.route('/webhook', methods=['POST'])
    def webhook():
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put(update)
        return jsonify({'status': 'ok'})
    
    @app.route('/set_webhook', methods=['GET'])
    def set_webhook():
        url = WEBHOOK_URL + '/webhook'
        application.bot.set_webhook(url)
        return jsonify({'status': 'webhook set', 'url': url})
    
    # راه‌اندازی سرور Flask
    if __name__ == '__main__':
        set_webhook()
        app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()

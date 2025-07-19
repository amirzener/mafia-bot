import os
import json
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

API_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DATA_FILE = "data.json"

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "owner_id": OWNER_ID,
            "admins": {
                "super_admins": [],
                "normal_admins": []
            },
            "chats": {},
            "panel": {}  # To store open panel info like {"user_id": message_id}
        }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main_menu_keyboard(user_id, data):
    kb = []
    if user_id == OWNER_ID:
        kb = [
            [InlineKeyboardButton("➕ افزودن مدیر ارشد", callback_data="add_super_admin")],
            [InlineKeyboardButton("➕ افزودن مدیر معمولی", callback_data="add_normal_admin")],
            [InlineKeyboardButton("📋 لیست مقام داران", callback_data="list_admins")],
            [InlineKeyboardButton("📋 لیست چت ها", callback_data="list_chats")],
            [InlineKeyboardButton("❌ بستن", callback_data="close")]
        ]
    elif user_id in data["admins"]["super_admins"]:
        kb = [
            [InlineKeyboardButton("➕ افزودن مدیر معمولی", callback_data="add_normal_admin")],
            [InlineKeyboardButton("📋 لیست مقام داران", callback_data="list_admins")],
            [InlineKeyboardButton("❌ بستن", callback_data="close")]
        ]
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ ربات فعال است.")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = load_data()
    text = update.message.text
    if text == "منو":
        if user_id == OWNER_ID or user_id in data["admins"]["super_admins"]:
            sent = await update.message.reply_text("📋 پنل شما", reply_markup=main_menu_keyboard(user_id, data))
            # ذخیره پیام پنل برای کنترل دسترسی دکمه‌ها
            data["panel"] = {"user_id": user_id, "message_id": sent.message_id}
            save_data(data)

    elif update.message.reply_to_message and text == "ست":
        # فقط مدیرارشد ها می تونن مدیر معمولی اضافه کنن
        if user_id in data["admins"]["super_admins"]:
            target_id = update.message.reply_to_message.from_user.id
            if target_id not in data["admins"]["normal_admins"]:
                data["admins"]["normal_admins"].append(target_id)
                save_data(data)
                await update.message.reply_text("✅ این کاربر به مدیر معمولی ارتقا یافت.")
            else:
                await update.message.reply_text("ℹ️ این کاربر قبلاً مدیر معمولی است.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = load_data()

    # چک کردن مالک پنل
    panel = data.get("panel", {})
    if not panel or user_id != panel.get("user_id") or query.message.message_id != panel.get("message_id"):
        await query.answer("⛔️ شما مجاز به استفاده از این پنل نیستید.", show_alert=True)
        return

    if query.data == "close":
        await query.message.delete()
        data["panel"] = {}
        save_data(data)
        return

    if query.data == "list_admins":
        text = f"📋 لیست مقام داران:\n👑 مالک: {data['owner_id']}\n"
        text += "🛡 مدیران ارشد: " + ", ".join(str(i) for i in data["admins"]["super_admins"]) + "\n"
        text += "👤 مدیران معمولی: " + ", ".join(str(i) for i in data["admins"]["normal_admins"])
        await query.message.edit_text(text, reply_markup=main_menu_keyboard(user_id, data))

    elif query.data == "list_chats":
        chats = data.get("chats", {})
        if not chats:
            await query.message.edit_text("هیچ گروه یا کانالی ثبت نشده است.", reply_markup=main_menu_keyboard(user_id, data))
            return
        text = "📋 لیست گروه ها و کانال ها:\n"
        for cid, info in chats.items():
            text += f"{info['title']} | {info['type']} | {cid}\n"
        await query.message.edit_text(text, reply_markup=main_menu_keyboard(user_id, data))

    elif query.data == "add_super_admin":
        # TODO: اضافه کردن مرحله برای وارد کردن آی دی مدیر ارشد
        await query.message.edit_text("❗️ این قسمت هنوز پیاده نشده است.", reply_markup=main_menu_keyboard(user_id, data))

    elif query.data == "add_normal_admin":
        # TODO: اضافه کردن مرحله برای وارد کردن آی دی مدیر معمولی
        await query.message.edit_text("❗️ این قسمت هنوز پیاده نشده است.", reply_markup=main_menu_keyboard(user_id, data))


async def my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # وقتی ربات عضو گروه یا کانال میشه، اطلاعات ذخیره بشه
    chat = update.my_chat_member.chat
    new_status = update.my_chat_member.new_chat_member.status
    if new_status in ("member", "administrator"):
        data = load_data()
        data["chats"][str(chat.id)] = {
            "title": chat.title or "-",
            "type": chat.type,
            "username": chat.username or "-"
        }
        save_data(data)


async def handle_webhook(request):
    # هندلر aiohttp برای وبهوک
    body = await request.json()
    update = Update.de_json(body)
    await application.update_queue.put(update)
    return web.Response(text="OK")


if __name__ == "__main__":
    application = ApplicationBuilder().token(API_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), menu))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.MY_CHAT_MEMBER, my_chat_member))

    # وبهوک aiohttp
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)

    async def on_startup(app):
        await application.bot.set_webhook(WEBHOOK_URL)

    async def on_shutdown(app):
        await application.bot.delete_webhook()

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    web.run_app(app, port=8080)

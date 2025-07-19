import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiohttp import web

API_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DATA_FILE = 'data.json'

# ------ مدیریت فایل JSON ------

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"owner_id": OWNER_ID, "admins": {"super_admins": [], "normal_admins": []}, "chats": {}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ------ دکمه ها ------

def main_menu_keyboard(user_id):
    kb = InlineKeyboardMarkup()
    if user_id == OWNER_ID:
        kb.add(InlineKeyboardButton("➕ افزودن مدیر ارشد", callback_data="add_super_admin"))
        kb.add(InlineKeyboardButton("➕ افزودن مدیر معمولی", callback_data="add_normal_admin"))
        kb.add(InlineKeyboardButton("📋 لیست مقام داران", callback_data="list_admins"))
        kb.add(InlineKeyboardButton("📋 لیست چت ها", callback_data="list_chats"))
        kb.add(InlineKeyboardButton("❌ بستن", callback_data="close"))
    elif user_id in load_data()["admins"]["super_admins"]:
        kb.add(InlineKeyboardButton("➕ افزودن مدیر معمولی", callback_data="add_normal_admin"))
        kb.add(InlineKeyboardButton("📋 لیست مقام داران", callback_data="list_admins"))
        kb.add(InlineKeyboardButton("❌ بستن", callback_data="close"))
    return kb

# ------ هندلر ها ------

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("✅ ربات فعال است.")

@dp.message()
async def handle_menu(message: types.Message):
    user_id = message.from_user.id
    data = load_data()
    if message.text == "منو":
        if user_id == OWNER_ID or user_id in data["admins"]["super_admins"]:
            sent = await message.answer("📋 پنل شما", reply_markup=main_menu_keyboard(user_id))
            data["panel_owner"] = sent.message_id
            data["panel_user"] = user_id
            save_data(data)

    elif message.reply_to_message and message.text == "ست":
        if user_id in data["admins"]["super_admins"]:
            target_id = message.reply_to_message.from_user.id
            if target_id not in data["admins"]["normal_admins"]:
                data["admins"]["normal_admins"].append(target_id)
                save_data(data)
                await message.reply("✅ این کاربر به مدیر معمولی ارتقا یافت.")
            else:
                await message.reply("ℹ️ این کاربر قبلاً مدیر معمولی است.")

@dp.callback_query()
async def panel_buttons(call: types.CallbackQuery):
    data = load_data()
    if call.message.message_id != data.get("panel_owner") or call.from_user.id != data.get("panel_user"):
        await call.answer("⛔️ شما مجاز به استفاده از این پنل نیستید.", show_alert=True)
        return

    if call.data == "close":
        await call.message.delete()

    elif call.data == "list_admins":
        text = "📋 لیست مقام داران:\n"
        text += "👑 مالک: {}\n".format(data["owner_id"])
        text += "🛡 مدیران ارشد: {}\n".format(', '.join(str(uid) for uid in data["admins"]["super_admins"]))
        text += "👤 مدیران معمولی: {}".format(', '.join(str(uid) for uid in data["admins"]["normal_admins"]))
        await call.message.edit_text(text, reply_markup=main_menu_keyboard(call.from_user.id))

    elif call.data == "list_chats":
        chats = data.get("chats", {})
        if not chats:
            await call.message.edit_text("هیچ گروه یا کانالی ثبت نشده است.", reply_markup=main_menu_keyboard(call.from_user.id))
            return
        text = "📋 لیست گروه ها و کانال ها:\n"
        for cid, info in chats.items():
            text += f"{info['title']} | {info['type']} | {cid}\n"
        await call.message.edit_text(text, reply_markup=main_menu_keyboard(call.from_user.id))

    await call.answer()

@dp.my_chat_member()
async def track_chats(update: types.ChatMemberUpdated):
    if update.new_chat_member.user.id == (await bot.me()).id and update.new_chat_member.status in ["member", "administrator"]:
        data = load_data()
        chat = update.chat
        data["chats"][str(chat.id)] = {
            "title": chat.title or "-",
            "type": chat.type,
            "username": chat.username or "-"
        }
        save_data(data)

# ------ وبهوک ------

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

app = web.Application()
app.add_routes([web.post('/webhook', dp.webhook_handler)])
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == '__main__':
    web.run_app(app, port=8080)

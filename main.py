import os
import json
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes



BOT_TOKEN = os.environ.get('BOT_TOKEN')
OWNER_ID = int(os.environ.get('OWNER_ID'))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

application = Application.builder().token(BOT_TOKEN).build()

ADMIN_FILE = "admin.json"
CHANNEL_FILE = "channel.json"
GROUP_FILE = "group.json"
ACTIVE_LIST_FILE = "activ_list.json"

for file in [ADMIN_FILE, CHANNEL_FILE, GROUP_FILE, ACTIVE_LIST_FILE]:
    if not os.path.exists(file):
        with open(file, "w", encoding='utf-8') as f:
            json.dump({}, f)

def load_json(file):
    try:
        with open(file, "r", encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_owner(uid):
    return uid == OWNER_ID

def is_admin(uid):
    admins = load_json(ADMIN_FILE)
    return str(uid) in admins

def is_owner_or_admin(uid):
    return is_owner(uid) or is_admin(uid)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    keyboard = [
        [InlineKeyboardButton("📋 گروه ها", callback_data="groups")],
        [InlineKeyboardButton("📢 کانال ها", callback_data="channels")],
        [InlineKeyboardButton("👤 ادمین ها", callback_data="admins")],
        [InlineKeyboardButton("❌ بستن", callback_data="close")]
    ]
    await update.message.reply_text("🔹 منوی مدیریت:", reply_markup=InlineKeyboardMarkup(keyboard))

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner_or_admin(update.effective_user.id):
        return
    await update.message.reply_text("⏰ لطفا ساعت را به صورت 4 رقمی ارسال کنید:")
    context.user_data['await_time'] = True

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('await_time'):
        text = update.message.text.strip()
        if len(text) == 4 and text.isdigit():
            active = load_json(ACTIVE_LIST_FILE)
            list_id = datetime.now().strftime('%Y%m%d%H%M%S')
            active[list_id] = {
                "creator": update.effective_user.id,
                "time": text,
                "players": [],
                "observers": [],
                "created_at": datetime.now().isoformat()
            }
            save_json(ACTIVE_LIST_FILE, active)
            channels = load_json(CHANNEL_FILE)
            for cid in channels:
                try:
                    keyboard = [[
                        InlineKeyboardButton("هستم", callback_data=f"join:{list_id}"),
                        InlineKeyboardButton("ناظر", callback_data=f"observe:{list_id}"),
                        InlineKeyboardButton("شروع", callback_data=f"start:{list_id}")
                    ]]
                    msg = await context.bot.send_message(chat_id=cid, text=f"🎮 ثبت نام بازی ساعت {text}", reply_markup=InlineKeyboardMarkup(keyboard))
                    active[list_id]['msg_id'] = msg.message_id
                    active[list_id]['channel_id'] = cid
                    save_json(ACTIVE_LIST_FILE, active)
                except:
                    continue
            await update.message.reply_text(f"✅ لیست بازی ساعت {text} ساخته شد.")
        else:
            await update.message.reply_text("⚠️ لطفا ساعت را صحیح وارد کنید.")
        context.user_data.pop('await_time')

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    active = load_json(ACTIVE_LIST_FILE)
    if data.startswith("join:"):
        lid = data.split(":")[1]
        if user_id not in active[lid]['players']:
            active[lid]['players'].append(user_id)
            save_json(ACTIVE_LIST_FILE, active)
            await query.answer("✅ به عنوان بازیکن ثبت شدید.")
        else:
            await query.answer("⚠️ شما قبلا ثبت شده‌اید.")
    elif data.startswith("observe:"):
        lid = data.split(":")[1]
        if is_owner_or_admin(user_id):
            if user_id not in active[lid]['observers']:
                active[lid]['observers'].append(user_id)
                save_json(ACTIVE_LIST_FILE, active)
                await query.answer("✅ به عنوان ناظر ثبت شدید.")
            else:
                await query.answer("⚠️ شما قبلا ناظر شده‌اید.")
        else:
            await query.answer("⛔ فقط ادمین می‌تواند ناظر شود.")
    elif data.startswith("start:"):
        lid = data.split(":")[1]
        if is_owner_or_admin(user_id):
            groups = load_json(GROUP_FILE)
            players = active[lid]['players']
            for gid in groups:
                mentions = " ".join([f"<a href='tg://user?id={p}'>.</a>" for p in players])
                try:
                    await context.bot.send_message(chat_id=gid, text=f"🎮 شروع بازی:\n{mentions}", parse_mode='HTML')
                except:
                    continue
            await context.bot.send_message(chat_id=active[lid]['channel_id'], text="🎮 بازی شروع شد.")
            await context.bot.delete_message(chat_id=active[lid]['channel_id'], message_id=active[lid]['msg_id'])
            active.pop(lid)
            save_json(ACTIVE_LIST_FILE, active)
            await query.answer("✅ بازی شروع شد.")
        else:
            await query.answer("⛔ فقط ادمین می‌تواند شروع کند.")
    else:
        await query.answer()

application.add_handler(CommandHandler("menu", menu))
application.add_handler(CommandHandler("list", list_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
application.add_handler(CallbackQueryHandler(callback_handler))

if __name__ == "__main__":
    application.run_webhook(listen="0.0.0.0", port=int(os.environ.get("PORT", 10000)), webhook_url=WEBHOOK_URL)

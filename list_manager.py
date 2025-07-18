from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from config import GET_TIME, TEXTS, LISTS_FILE
from data_manager import DataManager
from keyboard_manager import KeyboardManager
from access_control import AccessControl

async def create_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند ایجاد لیست جدید"""
    query = update.callback_query
    await query.answer()

    # بررسی وجود لیست فعال برای کاربر
    active_lists = DataManager.load_data(LISTS_FILE)
    for list_id, list_data in active_lists.items():
        if str(list_data["creator_id"]) == str(update.effective_user.id):
            await query.answer("شما در حال حاضر یک لیست فعال دارید!", show_alert=True)
            return ConversationHandler.END

    await query.edit_message_text(
    "⏰ لطفاً زمان شروع بازی را به صورت ۲۴ ساعته وارد کنید (مثال: ۱۹۳۰):",
    reply_markup=KeyboardManager.get_back_keyboard("main")
)
    return GET_TIME

async def process_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش زمان وارد شده توسط کاربر"""
    time_input = update.message.text.strip()
    
    # اعتبارسنجی زمان
    if not time_input.isdigit() or len(time_input) != 4:
        await update.message.reply_text(
            "❌ فرمت زمان نامعتبر! لطفاً به شکل ۲۴ ساعته وارد کنید (مثال: ۱۹۳۰)",
            reply_markup=KeyboardManager.get_back_keyboard("main")
        )
        return GET_TIME
    
    hour = int(time_input[:2])
    minute = int(time_input[2:])
    
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        await update.message.reply_text(
            "❌ زمان نامعتبر! لطفاً زمان صحیح وارد کنید",
            reply_markup=KeyboardManager.get_back_keyboard("main")
        )
        return GET_TIME
    
    # ایجاد لیست جدید
    list_id = str(len(DataManager.load_data(LISTS_FILE)) + 1)
    active_lists = DataManager.load_data(LISTS_FILE)
    
    active_lists[list_id] = {
        "creator_id": update.effective_user.id,
        "creator_name": update.effective_user.full_name,
        "time": f"{hour:02d}:{minute:02d}",
        "players": [],
        "observers": [],
        "channel_message_id": None
    }
    
    DataManager.save_data(LISTS_FILE, active_lists)
    
    await update.message.reply_text(
        "✅ لیست بازی با موفقیت ایجاد شد!",
        reply_markup=KeyboardManager.get_back_keyboard("main")
    )
    return ConversationHandler.END

def generate_list_text(list_id):
    """تولید متن لیست بازی"""
    active_lists = DataManager.load_data(LISTS_FILE)
    if list_id not in active_lists:
        return "❌ لیست یافت نشد!"

    list_data = active_lists[list_id]
    rainbow_colors = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "⚫", "⚪"]
    
    text = (
        f"🌟 *لیست بازی مافیا* 🌟\n\n"
        f"⏰ زمان شروع: {list_data['time']}\n"
        f"👤 سازنده: {list_data['creator_name']}\n\n"
        f"🎮 *بازیکنان:*\n" +
        ("\n".join(
            f"{rainbow_colors[i % len(rainbow_colors)]} {i+1}. [{player.split('|')[0]}](tg://user?id={player.split('|')[1]})"
            for i, player in enumerate(list_data['players']))
        ) if list_data['players'] else "هنوز بازیکنی وجود ندارد") +
        f"\n\n👁 *ناظران:*\n" +
        ("\n".join(
            f"{i+1}. 👁 [{obs.split('|')[0]}](tg://user?id={obs.split('|')[1]})"
            for i, obs in enumerate(list_data['observers']))
         if list_data['observers'] else "هنوز ناظری وجود ندارد"
   ) 
    return text

async def update_list_messages(list_id, context: ContextTypes.DEFAULT_TYPE):
    """به‌روزرسانی پیام‌های لیست در کانال‌ها"""
    active_lists = DataManager.load_data(LISTS_FILE)
    if list_id not in active_lists:
        return

    list_text = generate_list_text(list_id)
    is_privileged = AccessControl.is_privileged(int(active_lists[list_id]['creator_id']))
    
    channels = DataManager.load_data(CHANNELS_FILE)
    for channel_id in channels:
        try:
            await context.bot.edit_message_text(
                chat_id=channel_id,
                message_id=int(active_lists[list_id]['channel_message_id']),
                text=list_text,
                reply_markup=KeyboardManager.get_list_keyboard(list_id, is_privileged),
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"خطا در به‌روزرسانی لیست در کانال {channel_id}: {e}")

def setup_list_handlers(app):
    """تنظیم هندلرهای مربوط به لیست‌های بازی"""
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_list, pattern="^create_list$")],
        states={
            GET_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_time)]
        },
        fallbacks=[CallbackQueryHandler(back_handler, pattern="^back_to_")]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(join_list, pattern="^join_"))
    app.add_handler(CallbackQueryHandler(observe_list, pattern="^observe_"))
    app.add_handler(CallbackQueryHandler(start_game, pattern="^start_"))

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from config import GET_TIME, TEXTS
from data_manager import DataManager
from keyboard_manager import KeyboardManager

def generate_list_text(list_id):
    """تولید متن لیست بازی"""
    lists = DataManager.load_data(LISTS_FILE)
    if list_id not in lists:
        return "لیست یافت نشد!"
    
    game = lists[list_id]
    players = "\n".join([f"🔹 {p.split('|')[0]}" for p in game['players']]) or "هنوز بازیکنی وجود ندارد"
    observers = "\n".join([f"👁 {o.split('|')[0]}" for o in game['observers']]) or "هنوز ناظری وجود ندارد"
    
    return (
        f"🎮 لیست بازی مافیا 🎮\n\n"
        f"⏰ زمان شروع: {game['time']}\n"
        f"👤 سازنده: {game['creator_name']}\n\n"
        f"🔷 بازیکنان:\n{players}\n\n"
        f"👁 ناظران:\n{observers}"
    )

async def create_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند ایجاد لیست جدید"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "⏰ لطفاً زمان شروع بازی را به صورت ۲۴ ساعته وارد کنید (مثال: ۱۹۳۰):",
        reply_markup=KeyboardManager.get_back_keyboard("main")
    )
    return GET_TIME

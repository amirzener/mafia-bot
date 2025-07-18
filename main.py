import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from config import BOT_TOKEN, OWNER_ID
from data_manager import DataManager
from admin_manager import add_admin, save_admin
from list_manager import create_list, generate_list_text
from keyboard_manager import KeyboardManager

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: ContextTypes.DEFAULT_TYPE):
    """دستور شروع ربات"""
    await update.message.reply_text(
        "🤖 به ربات مدیریت لیست بازی مافیا خوش آمدید!",
        reply_markup=KeyboardManager.get_main_menu(update.effective_user.id)
    )

def main():
    """تابع اصلی اجرای ربات"""
    DataManager.initialize_files()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ثبت هندلرها
    app.add_handler(CommandHandler("start", start))
    
    # هندلرهای مدیریت ادمین
    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_admin, pattern="^add_admin$")],
        states={
            GET_ADMIN_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_admin)]
        },
        fallbacks=[]
    )
    app.add_handler(admin_conv)
    
    # هندلرهای لیست بازی
    list_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_list, pattern="^create_list$")],
        states={
            GET_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_time)]
        },
        fallbacks=[]
    )
    app.add_handler(list_conv)
    
    app.run_polling()

if __name__ == '__main__':
    main()

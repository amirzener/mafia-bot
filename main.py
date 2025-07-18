import os
import logging
from telegram import Update  # این import حیاتی بود که اضافه شد
from telegram.ext import ContextTypes
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,  # این import هم اضافه شد
    ConversationHandler
)
from config import BOT_TOKEN, PORT, WEBHOOK_URL
from data_manager import DataManager
from admin_manager import setup_admin_handlers
from list_manager import setup_list_handlers

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):  # نوع‌دهی پارامترها اضافه شد
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🤖 به ربات مدیریت لیست بازی مافیا خوش آمدید!"  # متن فارسی شد
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):  # نوع‌دهی اضافه شد
    logger.error(f"Update {update} caused error {context.error}")

def main():
    DataManager.initialize_files()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    setup_admin_handlers(app)
    setup_list_handlers(app)
    
    # Error handling
    app.add_error_handler(error_handler)
    
    # Webhook setup
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    main()

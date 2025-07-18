from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from config import GET_ADMIN_INFO, TEXTS, ADMINS_FILE, ROLE_ADMIN
from data_manager import DataManager
from keyboard_manager import KeyboardManager
from access_control import AccessControl

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not AccessControl.is_privileged(update.effective_user.id):
        await query.edit_message_text(TEXTS["errors"]["admin_only"])
        return ConversationHandler.END

    await query.edit_message_text(
        "لطفاً شناسه کاربری ادمین جدید را ارسال کنید:",
        reply_markup=KeyboardManager.get_back_keyboard("admin_management")
    )
    return GET_ADMIN_INFO

async def save_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text(
            "شناسه کاربری باید عدد باشد! لطفاً مجدداً وارد کنید:",
            reply_markup=KeyboardManager.get_back_keyboard("admin_management")
        )
        return GET_ADMIN_INFO

    new_admin_id = update.message.text
    admins = DataManager.load_data(ADMINS_FILE) or {}

    admins[new_admin_id] = {
        "name": f"ادمین {new_admin_id}",
        "role": ROLE_ADMIN
    }

    try:
        DataManager.save_data(ADMINS_FILE, admins)
    except Exception as e:
        await update.message.reply_text(
            f"خطا در ذخیره‌سازی اطلاعات: {e}",
            reply_markup=KeyboardManager.get_back_keyboard("admin_management")
        )
        return ConversationHandler.END

    await update.message.reply_text(
        TEXTS["success"]["admin_added"],
        reply_markup=KeyboardManager.get_back_keyboard("admin_management")
    )
    return ConversationHandler.END

def setup_admin_handlers(app):
    """تنظیم هندلرهای مدیریت ادمین"""
    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_admin, pattern="^add_admin$")],
        states={
            GET_ADMIN_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_admin)]
        },
        fallbacks=[CallbackQueryHandler(back_handler, pattern="^back_to_")]
    )
    app.add_handler(admin_conv)

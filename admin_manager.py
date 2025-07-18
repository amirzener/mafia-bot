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
        reply_markup=KeyboardManager.get_back_keyboard("manage_admins")
    )
    return GET_ADMIN_INFO

async def save_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text(
            "شناسه کاربری باید عدد باشد! لطفاً مجدداً وارد کنید:",
            reply_markup=KeyboardManager.get_back_keyboard("manage_admins")
        )
        return GET_ADMIN_INFO

    new_admin_id = update.message.text
    admins = DataManager.load_data(ADMINS_FILE) or {}

    admins[new_admin_id] = {
        "name": f"ادمین {new_admin_id}",
        "role": ROLE_ADMIN
    }

    DataManager.save_data(ADMINS_FILE, admins)

    await update.message.reply_text(
        TEXTS["success"]["admin_added"],
        reply_markup=KeyboardManager.get_back_keyboard("manage_admins")
    )
    return ConversationHandler.END

async def manage_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if not AccessControl.is_privileged(user_id):
        await query.edit_message_text(TEXTS["errors"]["admin_only"])
        return

    await query.edit_message_text(
        "🛠 به بخش مدیریت مدیران خوش آمدید",
        reply_markup=KeyboardManager.get_admins_keyboard(user_id)
    )

async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_main":
        await query.edit_message_text(
            "منوی اصلی",
            reply_markup=KeyboardManager.get_main_menu(query.from_user.id)
        )
    elif data == "back_to_manage_admins":
        await manage_admins(update, context)
    elif data == "back_to_manage_channels":
        await manage_channels(update, context)

def setup_admin_handlers(app):
    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_admin, pattern="^add_admin$")],
        states={
            GET_ADMIN_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_admin)]
        },
        fallbacks=[CallbackQueryHandler(back_handler, pattern="^back_to_")]
    )
    app.add_handler(admin_conv)
    app.add_handler(CallbackQueryHandler(manage_admins, pattern="^manage_admins$"))
    app.add_handler(CallbackQueryHandler(back_handler, pattern="^back_to_"))

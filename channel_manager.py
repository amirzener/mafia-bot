import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler
)
from data_manager import DataManager
from keyboard_manager import KeyboardManager
from config import CHANNELS_FILE

async def manage_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    channels = DataManager.load_data(CHANNELS_FILE) or {}

    if not channels:
        await query.edit_message_text(
            "❌ هیچ کانالی ثبت نشده است.",
            reply_markup=KeyboardManager.get_back_keyboard("main")
        )
        return

    buttons = []
    for channel_id, channel_data in channels.items():
        title = channel_data.get("title", "کانال بدون نام")
        buttons.append([
            InlineKeyboardButton(
                text=f"{title} (ID: {channel_id})",
                callback_data=f"noop"  # فقط نمایش، کلیک روی خود نام کاری ندارد
            ),
            InlineKeyboardButton(
                text="❌ حذف",
                callback_data=f"remove_channel_{channel_id}"
            )
        ])

    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])

    await query.edit_message_text(
        "📢 کانال‌های ثبت‌شده:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data  # مثلاً "remove_channel_-1001234567890"
    channel_id = data.replace("remove_channel_", "")

    channels = DataManager.load_data(CHANNELS_FILE) or {}

    if channel_id not in channels:
        await query.answer("کانال یافت نشد!", show_alert=True)
        return

    try:
        # ابتدا ربات را از کانال حذف می‌کنیم
        await context.bot.leave_chat(chat_id=channel_id)
    except Exception as e:
        logging.error(f"خطا هنگام خروج از کانال {channel_id}: {e}")
        await query.answer(f"خطا هنگام خروج از کانال: {e}", show_alert=True)
        return

    # حذف کانال از فایل داده‌ها
    del channels[channel_id]
    DataManager.save_data(CHANNELS_FILE, channels)

    await query.edit_message_text(
        "کانال با موفقیت حذف شد.",
        reply_markup=KeyboardManager.get_back_keyboard("manage_channels")
    )


def setup_channel_handlers(app):
    app.add_handler(CallbackQueryHandler(manage_channels, pattern="^manage_channels$"))
    app.add_handler(CallbackQueryHandler(remove_channel, pattern="^remove_channel_"))

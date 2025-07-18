import asyncio
import logging
import os

from aiogram
import Bot, Dispatcher, F, types 
from aiogram.enums
import ParseMode
from aiogram.types
import Message, CallbackQuery 
from aiogram.filters 
import CommandStart 
from aiogram.fsm.storage.memory 
import MemoryStorage 
from dotenv 
import load_dotenv

from config 
import OWNER_ID 
from access_control 
import get_user_role 
from keyboard_manager 
import get_main_menu 
from admin_manager 
import add_super_admin, add_admin, list_all_admins 
from list_manager 
import create_list, send_list_message_in_channels, add_member_to_list, add_observer_to_list, notify_members_in_groups 
from data_manager 
import get_channels, get_groups

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN") WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML) dp = Dispatcher(storage=MemoryStorage())

pending_actions = {}

@dp.message(CommandStart()) async def start_handler(message: Message): user_id = str(message.from_user.id) role = get_user_role(user_id)

if role == "owner":
    text = "<b>🛡️ به پنل مالک خوش آمدید</b>\nاز منوی زیر استفاده کنید."
elif role == "super_admin":
    text = "<b>👑 به پنل ادمین ویژه خوش آمدید</b>\nاز منوی زیر استفاده کنید."
elif role == "admin":
    text = "<b>🧩 به پنل ادمین معمولی خوش آمدید</b>\nاز منوی زیر استفاده کنید."
else:
    text = "<b>🎉 خوش آمدید</b>\nبرای شما منویی وجود ندارد."

keyboard = get_main_menu(role, user_id)
await message.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("add_super_admin:")) async def handle_add_super_admin(callback: CallbackQuery): user_id = str(callback.from_user.id) data_owner = callback.data.split(":")[1] if user_id != data_owner: await callback.answer("⛔️ این منو برای شما نیست.", show_alert=True) return pending_actions[user_id] = "add_super_admin" await callback.message.answer("لطفا آی دی عددی ادمین ویژه را ارسال کنید.")

@dp.callback_query(F.data.startswith("add_admin:")) async def handle_add_admin(callback: CallbackQuery): user_id = str(callback.from_user.id) data_owner = callback.data.split(":")[1] if user_id != data_owner: await callback.answer("⛔️ این منو برای شما نیست.", show_alert=True) return pending_actions[user_id] = "add_admin" await callback.message.answer("لطفا آی دی عددی ادمین معمولی را ارسال کنید.")

@dp.callback_query(F.data.startswith("list_admins:")) async def handle_list_admins(callback: CallbackQuery): user_id = str(callback.from_user.id) data_owner = callback.data.split(":")[1] if user_id != data_owner: await callback.answer("⛔️ این منو برای شما نیست.", show_alert=True) return admins = list_all_admins() text = "<b>👤 لیست مدیران:</b>\n\n" text += "👑 ادمین‌های ویژه:\n" + "\n".join(admins.get("super_admins", [])) + "\n\n" text += "🧩 ادمین‌های معمولی:\n" + "\n".join(admins.get("admins", [])) await callback.message.answer(text)

@dp.callback_query(F.data.startswith("create_list:")) async def handle_create_list(callback: CallbackQuery): user_id = str(callback.from_user.id) data_owner = callback.data.split(":")[1] if user_id != data_owner: await callback.answer("⛔️ این منو برای شما نیست.", show_alert=True) return pending_actions[user_id] = "create_list" await callback.message.answer("🕑 لطفا ساعت را ارسال کنید (مثال: 22:30)")

@dp.callback_query(F.data.startswith("im_here:")) async def handle_im_here(callback: CallbackQuery): _, list_id, data_owner = callback.data.split(":") user_id = str(callback.from_user.id) if user_id != data_owner: await callback.answer("⛔️ این دکمه برای شما نیست.", show_alert=True) return user_name = callback.from_user.full_name add_member_to_list(list_id, user_name) await callback.answer("✅ حضور شما ثبت شد.", show_alert=True)

@dp.callback_query(F.data.startswith("observer:")) async def handle_observer(callback: CallbackQuery): _, list_id, data_owner = callback.data.split(":") user_id = str(callback.from_user.id) role = get_user_role(user_id) if role not in ["owner", "super_admin", "admin"]: await callback.answer("⛔️ فقط مدیران مجاز به ثبت به عنوان ناظر هستند.", show_alert=True) return user_name = callback.from_user.full_name add_observer_to_list(list_id, user_name) await callback.answer("✅ به عنوان ناظر ثبت شدید.", show_alert=True)

@dp.callback_query(F.data.startswith("start_list:")) async def handle_start_list(callback: CallbackQuery): _, list_id, data_owner = callback.data.split(":") user_id = str(callback.from_user.id) if user_id != data_owner: await callback.answer("⛔️ این دکمه برای شما نیست.", show_alert=True) return groups = get_groups() await notify_members_in_groups(bot, list_id, groups) await callback.message.answer("✅ تمام اعضای لیست در گروه‌ها تگ شدند و اعلان ارسال شد.")

@dp.message() async def handle_pending_actions(message: Message): user_id = str(message.from_user.id) if user_id not in pending_actions: return action = pending_actions.pop(user_id)

if action == "add_super_admin":
    target_id = message.text.strip()
    if add_super_admin(target_id):
        await message.answer("✅ ادمین ویژه اضافه شد.")
    else:
        await message.answer("⚠️ این کاربر از قبل ادمین ویژه است.")

elif action == "add_admin":
    target_id = message.text.strip()
    if add_admin(target_id):
        await message.answer("✅ ادمین معمولی اضافه شد.")
    else:
        await message.answer("⚠️ این کاربر از قبل ادمین معمولی است.")

elif action == "create_list":
    hour = message.text.strip()
    list_id = f"list_{user_id}_{hour.replace(':', '_')}"
    create_list(list_id, hour)
    channels = get_channels()
    await send_list_message_in_channels(bot, list_id, channels, user_id)
    await message.answer("✅ لیست ایجاد و در کانال‌ها ارسال شد.")

async def on_startup(bot: Bot): if WEBHOOK_URL: await bot.set_webhook(WEBHOOK_URL) logger.info(f"Webhook set to {WEBHOOK_URL}") else: logger.info("Polling mode active")

async def main(): try: await on_startup(bot) await dp.start_polling(bot) except Exception as e: logger.error(f"Error: {e}")

if name == "main": asyncio.run(main())


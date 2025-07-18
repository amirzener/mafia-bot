import asyncio import logging import os from aiogram import Bot, Dispatcher, F, types from aiogram.enums import ParseMode from aiogram.types import Message from aiogram.filters import CommandStart from aiogram.fsm.storage.memory import MemoryStorage from dotenv import load_dotenv

from config import OWNER_ID from access_control import get_user_role from keyboard_manager import get_main_menu

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN") WEBHOOK_URL = os.getenv("WEBHOOK_URL")

Logging

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML) dp = Dispatcher(storage=MemoryStorage())

/start handler

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

async def on_startup(bot: Bot): if WEBHOOK_URL: await bot.set_webhook(WEBHOOK_URL) logger.info(f"Webhook set to {WEBHOOK_URL}") else: logger.info("Polling mode active")

async def main(): try: await on_startup(bot) await dp.start_polling(bot) except Exception as e: logger.error(f"Error: {e}")

if name == "main": asyncio.run(main())


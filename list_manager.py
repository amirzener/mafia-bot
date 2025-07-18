import datetime from aiogram import Bot from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton from config import OWNER_ID from data_manager import get_lists, save_lists from access_control import get_user_role

LIST_PREFIX = "list_"

def create_list(list_id: str, hour: str): lists = get_lists() lists[list_id] = { "hour": hour, "members": [], "observers": [], "created_at": datetime.datetime.now().isoformat() } save_lists(lists)

def add_member_to_list(list_id: str, user_id: str, name: str) -> bool: lists = get_lists() if list_id not in lists: return False if user_id not in [u["id"] for u in lists[list_id]["members"]]: lists[list_id]["members"].append({"id": user_id, "name": name}) save_lists(lists) return True

def add_observer_to_list(list_id: str, user_id: str, name: str) -> bool: lists = get_lists() if list_id not in lists: return False if user_id not in [u["id"] for u in lists[list_id]["observers"]]: lists[list_id]["observers"].append({"id": user_id, "name": name}) save_lists(lists) return True

def get_list_info(list_id: str) -> dict: lists = get_lists() return lists.get(list_id, {})

async def send_list_message_in_channels(bot: Bot, list_id: str, channels: list): keyboard = InlineKeyboardMarkup() keyboard.add(InlineKeyboardButton(text="✅ هستم", callback_data=f"im_here:{list_id}")) keyboard.add(InlineKeyboardButton(text="🛡️ ناظر", callback_data=f"observer:{list_id}")) keyboard.add(InlineKeyboardButton(text="🚀 شروع", callback_data=f"start_list:{list_id}"))

for channel_id in channels:
    try:
        await bot.send_message(chat_id=channel_id, text="📝 ثبت حضور لیست جدید", reply_markup=keyboard)
    except Exception as e:
        print(f"Error sending to {channel_id}: {e}")

async def notify_members_in_groups(bot: Bot, list_id: str, groups: list): info = get_list_info(list_id) if not info: return

text = "🔔 لیست حضور: \n"
for member in info["members"]:
    text += f"[{member['name']}](tg://user?id={member['id']}) ",
text += "\nحضور الزامی است."

for group_id in groups:
    try:
        await bot.send_message(chat_id=group_id, text=text, parse_mode="Markdown")
    except Exception as e:
        print(f"Error notifying {group_id}: {e}")


import json import os from typing import Any from config import ADMINS_FILE, CHANNELS_FILE, LISTS_FILE, USERS_FILE

def load_json(file_path: str) -> Any: if not os.path.exists(file_path): with open(file_path, "w", encoding="utf-8") as f: json.dump({}, f, ensure_ascii=False, indent=2)

with open(file_path, "r", encoding="utf-8") as f:
    return json.load(f)

def save_json(file_path: str, data: Any): with open(file_path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def get_admins(): return load_json(ADMINS_FILE)

def save_admins(data): save_json(ADMINS_FILE, data)

def get_channels(): return load_json(CHANNELS_FILE)

def save_channels(data): save_json(CHANNELS_FILE, data)

def get_lists(): return load_json(LISTS_FILE)

def save_lists(data): save_json(LISTS_FILE, data)

def get_users(): return load_json(USERS_FILE)

def save_users(data): save_json(USERS_FILE, data)


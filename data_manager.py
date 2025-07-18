import json
import os
from config import OWNER_ID
from config import ADMINS_FILE, CHANNELS_FILE, LISTS_FILE, USERS_FILE

class DataManager:
    @staticmethod
    def load_data(filename, default=None):
        """بارگذاری داده از فایل JSON"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default or {}

    @staticmethod  
    def save_data(filename, data):  
        """ذخیره داده در فایل JSON"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:  
            json.dump(data, f, ensure_ascii=False, indent=4)

    @staticmethod  
    def initialize_files():  
        """ایجاد فایل‌های اولیه"""
        initial_data = {
            ADMINS_FILE: {
                str(OWNER_ID): {
                    "name": "مالک ربات",
                    "role": ROLE_OWNER
                }
            },
            CHANNELS_FILE: {},
            LISTS_FILE: {},
            USERS_FILE: {}
        }
        
        for filename, data in initial_data.items():
            if not os.path.exists(filename):
                DataManager.save_data(filename, data)

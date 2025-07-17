import json
import os
from config import ADMINS_FILE, CHANNELS_FILE, LISTS_FILE, USERS_FILE

class DataManager:
    @staticmethod
    def load_data(filename, default=None):
        """بارگذاری داده‌ها از فایل JSON"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default or {}

    @staticmethod  
    def save_data(filename, data):  
        """ذخیره داده‌ها در فایل JSON"""
        with open(filename, 'w', encoding='utf-8') as f:  
            json.dump(data, f, ensure_ascii=False, indent=4)

    @staticmethod  
    def initialize_files():  
        """مقداردهی اولیه فایل‌های داده"""
        files = {  
            ADMINS_FILE: {  
                str(os.getenv('OWNER_ID')): {  
                    "name": "Owner",  
                    "role": "owner"  
                }  
            },  
            CHANNELS_FILE: {},  
            LISTS_FILE: {},  
            USERS_FILE: {}  
        }  
        for filename, default_data in files.items():  
            if not os.path.exists(filename):
                DataManager.save_data(filename, default_data)

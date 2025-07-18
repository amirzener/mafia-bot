from data_manager import DataManager
from config import ADMINS_FILE, ROLE_OWNER, ROLE_SUPER_ADMIN, ROLE_ADMIN, OWNER_ID

class AccessControl:
    @staticmethod
    def is_owner(user_id):
        """بررسی اینکه کاربر مالک ربات است"""
        return str(user_id) == str(OWNER_ID)

    @staticmethod  
    def is_super_admin(user_id):  
        """بررسی سوپر ادمین بودن"""
        admins = DataManager.load_data(ADMINS_FILE)  
        return str(user_id) in admins and admins[str(user_id)]["role"] == ROLE_SUPER_ADMIN  

    @staticmethod  
    def is_admin(user_id):  
        """بررسی ادمین بودن"""
        admins = DataManager.load_data(ADMINS_FILE)  
        return str(user_id) in admins and admins[str(user_id)]["role"] in [ROLE_ADMIN, ROLE_SUPER_ADMIN]  

    @staticmethod  
    def is_privileged(user_id):  
        """بررسی دسترسی ویژه"""
        return AccessControl.is_owner(user_id) or AccessControl.is_admin(user_id)

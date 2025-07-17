from data_manager import DataManager
from config import ADMINS_FILE, ROLE_OWNER, ROLE_SUPER_ADMIN, ROLE_ADMIN

class AccessControl:
    @staticmethod
    def is_owner(user_id):
        """بررسی مالک بودن کاربر"""
        return str(user_id) == str(os.getenv('OWNER_ID'))

    @staticmethod  
    def is_super_admin(user_id):  
        """بررسی سوپر ادمین بودن کاربر"""
        admins = DataManager.load_data(ADMINS_FILE)  
        return str(user_id) in admins and admins[str(user_id)]["role"] == ROLE_SUPER_ADMIN  

    @staticmethod  
    def is_admin(user_id):  
        """بررسی ادمین بودن کاربر"""
        admins = DataManager.load_data(ADMINS_FILE)  
        return str(user_id) in admins and admins[str(user_id)]["role"] in [ROLE_ADMIN, ROLE_SUPER_ADMIN]  

    @staticmethod  
    def is_privileged(user_id):  
        """بررسی دسترسی ویژه کاربر"""
        return AccessControl.is_owner(user_id) or AccessControl.is_admin(user_id)

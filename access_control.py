from config import OWNER_ID, get_admins, ROLE_OWNER, ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER

def get_user_role(user_id: str) -> str: if user_id == OWNER_ID: return ROLE_OWNER

admins = get_admins()

if user_id in admins.get("super_admins", []):
    return ROLE_SUPER_ADMIN
elif user_id in admins.get("admins", []):
    return ROLE_ADMIN
else:
    return ROLE_USER

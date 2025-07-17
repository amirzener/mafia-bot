import os

# Configuration
OWNER_ID = int(os.environ.get('OWNER_ID'))
BOT_TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
ADMINS_FILE = "admins.json"
CHANNELS_FILE = "channels.json"
LISTS_FILE = "active_lists.json"
USERS_FILE = "users.json"

# Role definitions
ROLE_OWNER = "owner"
ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"

# Conversation states
GET_TIME, GET_ADMIN_INFO, GET_SUPER_ADMIN_INFO = range(3)

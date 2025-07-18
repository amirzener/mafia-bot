import os

# تنظیمات اصلی
OWNER_ID = int(os.environ.get('OWNER_ID'))
BOT_TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
PORT = int(os.environ.get('PORT')) 
# فایل‌های دیتابیس
ADMINS_FILE = "list_manager/admins.json"
CHANNELS_FILE = "list_manager/channels.json"
LISTS_FILE = "list_manager/lists.json"
USERS_FILE = "list_manager/users.json"

# مجوزها
ROLE_OWNER = "owner"
ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"
ROLE_USER = "user"
# حالت‌های گفتگو
GET_TIME, GET_ADMIN_INFO, GET_SUPER_ADMIN_INFO = range(3)

# متن‌های فارسی
TEXTS = {
    "start": "🤖 به ربات مدیریت لیست بازی مافیا خوش آمدید!",
    "errors": {
        "owner_only": "❌ فقط مالک ربات می‌تواند این عمل را انجام دهد!",
        "admin_only": "❌ فقط مدیران می‌توانند این عمل را انجام دهند!",
        "channel_not_found": "❌ کانال یافت نشد!",
        "time_format": "❌ فرمت زمان نامعتبر! لطفاً به شکل ۲۴ ساعته وارد کنید (مثال: ۱۹۳۰)"
    },
    "success": {
        "admin_added": "✅ ادمین با موفقیت اضافه شد!",
        "list_created": "✅ لیست بازی با موفقیت ایجاد شد!"
    }
}

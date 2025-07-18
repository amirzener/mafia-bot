import os

# تنظیمات اصلی
OWNER_ID = int(os.environ.get('OWNER_ID', 123456789))
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'your_bot_token')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://yourdomain.com/webhook')

# فایل‌های دیتابیس
ADMINS_FILE = "data/admins.json"
CHANNELS_FILE = "data/channels.json"
LISTS_FILE = "data/active_lists.json"
USERS_FILE = "data/users.json"

# سطوح دسترسی
ROLE_OWNER = "مالک"
ROLE_SUPER_ADMIN = "سوپرادمین"
ROLE_ADMIN = "ادمین"

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

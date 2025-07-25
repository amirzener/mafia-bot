const { Telegraf } = require('telegraf');
const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');

dotenv.config();

// تنظیمات اولیه
const BOT_TOKEN = process.env.BOT_TOKEN;
const OWNER_ID = parseInt(process.env.OWNER_ID);
const WEBHOOK_URL = process.env.WEBHOOK_URL;

const bot = new Telegraf(BOT_TOKEN);

// تنظیم session (قبل از همه middlewareها)
const localSession = new LocalSession({
  database: 'session_db.json' // فایل ذخیره sessionها
});
bot.use(localSession.middleware());

// مسیر فایل‌های JSON
const ADMIN_FILE = "admin.json";
const CHANNEL_FILE = "channel.json";
const GROUP_FILE = "group.json";
const ACTIVE_LIST_FILE = "active_list.json";

// توابع کمکی برای مدیریت فایل‌های JSON
function loadJson(filePath) {
    try {
        const data = fs.readFileSync(filePath, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        return {};
    }
}

function saveJson(filePath, data) {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 4), 'utf8');
}

// ایجاد فایل‌های JSON در صورت عدم وجود
[ADMIN_FILE, CHANNEL_FILE, GROUP_FILE, ACTIVE_LIST_FILE].forEach(file => {
    if (!fs.existsSync(file)) {
        saveJson(file, {});
    }
});

// توابع کمکی برای بررسی دسترسی
function isOwner(userId) {
    return userId === OWNER_ID;
}

function isAdmin(userId) {
    const admins = loadJson(ADMIN_FILE);
    return admins.hasOwnProperty(userId.toString());
}

function isOwnerOrAdmin(userId) {
    return isOwner(userId) || isAdmin(userId);
}

function isValidTime(timeStr) {
    if (timeStr.length !== 4 || !/^\d+$/.test(timeStr)) return false;
    const hours = parseInt(timeStr.substring(0, 2));
    const minutes = parseInt(timeStr.substring(2));
    return hours >= 0 && hours < 24 && minutes >= 0 && minutes < 60;
}

// مدیریت اضافه شدن به گروه/کانال جدید
bot.on('new_chat_members', async (ctx) => {
    const chat = ctx.chat;
    const botId = ctx.botInfo.id;
    
    if (ctx.message.new_chat_members.some(member => member.id === botId)) {
        if (chat.type === 'channel') {
            const channels = loadJson(CHANNEL_FILE);
            channels[chat.id] = {
                title: chat.title,
                username: chat.username,
                invite_link: chat.invite_link,
                date_added: new Date().toISOString()
            };
            saveJson(CHANNEL_FILE, channels);
            await ctx.telegram.sendMessage(
                OWNER_ID,
                `✅ به کانال اضافه شد:\n${chat.title}\nID: ${chat.id}`
            );
        } else if (chat.type === 'group' || chat.type === 'supergroup') {
            const groups = loadJson(GROUP_FILE);
            groups[chat.id] = {
                title: chat.title,
                username: chat.username,
                invite_link: chat.invite_link,
                date_added: new Date().toISOString()
            };
            saveJson(GROUP_FILE, groups);
            await ctx.telegram.sendMessage(
                OWNER_ID,
                `✅ به گروه اضافه شد:\n${chat.title}\nID: ${chat.id}`
            );
        }
    }
});

// دستورات ربات
bot.command('start', async (ctx) => {
    if (isOwner(ctx.from.id)) {
        await ctx.reply('اومدم');
    }
});

bot.command('menu', async (ctx) => {
    if (!isOwner(ctx.from.id)) return;
    
    const keyboard = {
        inline_keyboard: [
            [{ text: '📋 نمایش لیست گروه ها', callback_data: 'show_groups' }],
            [{ text: '📢 نمایش لیست کانال ها', callback_data: 'show_channels' }],
            [{ text: '👤 نمایش لیست ادمین ها', callback_data: 'show_admins' }],
            [{ text: '❌ بستن پنل', callback_data: 'close_panel' }]
        ]
    };
    
    await ctx.reply('🔹 پنل مدیریت ربات 🔹', { reply_markup: keyboard });
});

bot.command('list', async (ctx) => {
    if (!isOwnerOrAdmin(ctx.from.id)) return;
    
    await ctx.reply(
        "⏰ ساعت را به صورت 4 رقمی وارد کنید (مثال: 1930):\n\n" +
        "برای لغو عملیات می‌توانید از دستور /cancel استفاده کنید."
    );
    ctx.session = { waitingForTime: true, listCommandSender: ctx.from.id };
});

bot.command('cancel', async (ctx) => {
    if (ctx.session?.waitingForTime) {
        ctx.session = {};
        await ctx.reply("❌ عملیات ایجاد لیست لغو شد.");
    } else {
        await ctx.reply("⚠️ هیچ عملیاتی در حال انجام نیست که نیاز به لغو داشته باشد.");
    }
});

// مدیریت پیام‌های متنی
bot.on('text', async (ctx) => {
    if (ctx.session?.waitingForTime && ctx.from.id === ctx.session.listCommandSender) {
        const timeStr = ctx.message.text.trim();
        
        if (!isValidTime(timeStr)) {
            await ctx.reply(
                "⚠️ ساعت وارد شده معتبر نیست. لطفا یک ساعت معتبر به صورت 4 رقمی وارد کنید (مثال: 1930):\n\n" +
                "برای لغو عملیات می‌توانید از دستور /cancel استفاده کنید."
            );
            return;
        }

        // ایجاد لیست فعال جدید
        const activeList = loadJson(ACTIVE_LIST_FILE);
        const listId = new Date().toISOString().replace(/[-:.]/g, '');
            
        activeList[listId] = {
            creator: ctx.from.id,
            time: timeStr,
            players: [],
            observers: [],
            created_at: new Date().toISOString()
        };
        saveJson(ACTIVE_LIST_FILE, activeList);
            
        // ارسال پیام به کانال‌ها
        const channels = loadJson(CHANNEL_FILE);
        for (const channelId in channels) {
            try {
                const keyboard = {
                    inline_keyboard: [
                        [{ text: '🎮 هستم', callback_data: `join_player:${listId}` }],
                        [{ text: '👁️ ناظر', callback_data: `join_observer:${listId}` }],
                        [{ text: '🚀 شروع', callback_data: `start_game:${listId}` }]
                    ]
                };
                    
                const sentMsg = await ctx.telegram.sendMessage(
                    channelId,
                    `Jurassic Mafia Groups\n\nجهت حضور در لابی نام خود را ثبت کنید.\nسازنده: ${ctx.from.first_name}\nساعت: ${timeStr.substring(0, 2)}:${timeStr.substring(2)}\n\nبازیکنان:\nهنوز بازیکنی ثبت نام نکرده است.`,
                    { reply_markup: keyboard, parse_mode: 'Markdown' }
                );
                    
                // ذخیره اطلاعات پیام
                activeList[listId].channelMessageId = sentMsg.message_id;
                activeList[listId].channelId = channelId;
                saveJson(ACTIVE_LIST_FILE, activeList);
            } catch (error) {
                console.error(`Error sending to channel ${channelId}:`, error);
            }
        }
        
        await ctx.reply(`✅ لیست بازی برای ساعت ${timeStr.substring(0, 2)}:${timeStr.substring(2)} ایجاد شد.`);
        ctx.session = {};
    }
});

// مدیریت رویدادهای دکمه‌ها
bot.on('callback_query', async (ctx) => {
    const data = ctx.callbackQuery.data;
    const userId = ctx.from.id;
    
    if (data.startsWith('join_player:') || data.startsWith('join_observer:') || data.startsWith('start_game:')) {
        await handleGameActions(ctx);
        return;
    }

    if (!isOwner(userId)) {
        await ctx.answerCbQuery('⛔ شما مجاز به استفاده از این پنل نیستید.');
        return;
    }

    if (data === 'show_groups') {
        await showGroupsMenu(ctx);
    } else if (data === 'show_channels') {
        await showChannelsMenu(ctx);
    } else if (data === 'show_admins') {
        await showAdminsList(ctx);
    } else if (data === 'back_to_main') {
        await showMainMenu(ctx);
    } else if (data === 'close_panel') {
        await ctx.deleteMessage();
    } else if (data.startsWith('leave_chat:')) {
        const [, chatId, chatType] = data.split(':');
        try {
            await ctx.telegram.leaveChat(chatId);
            
            if (chatType === 'group') {
                const groups = loadJson(GROUP_FILE);
                delete groups[chatId];
                saveJson(GROUP_FILE, groups);
            } else {
                const channels = loadJson(CHANNEL_FILE);
                delete channels[chatId];
                saveJson(CHANNEL_FILE, channels);
            }
            
            await ctx.answerCbQuery(`✅ از ${chatType} خارج شد.`);
            if (chatType === 'group') {
                await showGroupsMenu(ctx);
            } else {
                await showChannelsMenu(ctx);
            }
        } catch (error) {
            await ctx.answerCbQuery(`❌ خطا در خارج شدن: ${error.message}`);
        }
    }
});

// توابع منو
async function showMainMenu(ctx) {
    const keyboard = {
        inline_keyboard: [
            [{ text: '📋 نمایش لیست گروه ها', callback_data: 'show_groups' }],
            [{ text: '📢 نمایش لیست کانال ها', callback_data: 'show_channels' }],
            [{ text: '👤 نمایش لیست ادمین ها', callback_data: 'show_admins' }],
            [{ text: '❌ بستن پنل', callback_data: 'close_panel' }]
        ]
    };
    
    if (ctx.callbackQuery) {
        await ctx.editMessageText('🔹 پنل مدیریت ربات 🔹', { reply_markup: keyboard });
    } else {
        await ctx.reply('🔹 پنل مدیریت ربات 🔹', { reply_markup: keyboard });
    }
}

async function showGroupsMenu(ctx) {
    const groups = loadJson(GROUP_FILE);
    const keyboard = { inline_keyboard: [] };

    for (const groupId in groups) {
        keyboard.inline_keyboard.push([
            { 
                text: `🚫 ${groups[groupId].title}`,
                callback_data: `leave_chat:${groupId}:group`
            }
        ]);
    }

    keyboard.inline_keyboard.push([{ text: '🔙 بازگشت', callback_data: 'back_to_main' }]);
    
    await ctx.editMessageText('📋 لیست گروه ها:', { reply_markup: keyboard });
}

async function showChannelsMenu(ctx) {
    const channels = loadJson(CHANNEL_FILE);
    const keyboard = { inline_keyboard: [] };

    for (const channelId in channels) {
        keyboard.inline_keyboard.push([
            { 
                text: `🚫 ${channels[channelId].title}`,
                callback_data: `leave_chat:${channelId}:channel`
            }
        ]);
    }

    keyboard.inline_keyboard.push([{ text: '🔙 بازگشت', callback_data: 'back_to_main' }]);
    
    await ctx.editMessageText('📢 لیست کانال ها:', { reply_markup: keyboard });
}

async function showAdminsList(ctx) {
    const admins = loadJson(ADMIN_FILE);
    let adminList = '';
    
    for (const adminId in admins) {
        adminList += `👤 ${admins[adminId].alias} - ${adminId}\n`;
    }

    const keyboard = {
        inline_keyboard: [[{ text: '🔙 بازگشت', callback_data: 'back_to_main' }]]
    };
    
    await ctx.editMessageText(`👥 لیست ادمین ها:\n\n${adminList}`, { 
        reply_markup: keyboard,
        parse_mode: 'Markdown'
    });
}

// مدیریت عملیات بازی
async function handleGameActions(ctx) {
    const data = ctx.callbackQuery.data;
    const userId = ctx.from.id;
    const [action, listId] = data.split(':');
    const activeList = loadJson(ACTIVE_LIST_FILE);
    const listData = activeList[listId];

    if (!listData) {
        await ctx.answerCbQuery('❌ این لیست منقضی شده است.');
        return;
    }

    if (action === 'join_player') {
        const user = ctx.from;
        const username = `[${user.first_name}](tg://user?id=${user.id})`;
        
        if (!listData.players.some(p => p.id === userId)) {
            listData.players.push({ id: userId, name: username });
            activeList[listId] = listData;
            saveJson(ACTIVE_LIST_FILE, activeList);
            await ctx.answerCbQuery('✅ شما به عنوان بازیکن ثبت نام کردید.');
        } else {
            await ctx.answerCbQuery('⚠️ شما قبلا ثبت نام کرده اید.');
        }

        await updateActiveListMessage(listId, ctx.telegram);
    } else if (action === 'join_observer') {
        if (!isOwnerOrAdmin(userId)) {
            await ctx.answerCbQuery('⛔ فقط ادمین ها می‌توانند ناظر باشند.');
            return;
        }

        if (listData.observers.length >= 2) {
            await ctx.answerCbQuery('⚠️ حد مجاز ناظرین (2 نفر) تکمیل شده است.');
            return;
        }
            
        if (!listData.observers.some(o => o.id === userId)) {
            const user = ctx.from;
            const username = `[${user.first_name}](tg://user?id=${user.id})`;
            listData.observers.push({ id: userId, name: username });
            activeList[listId] = listData;
            saveJson(ACTIVE_LIST_FILE, activeList);
            await ctx.answerCbQuery('✅ شما به عنوان ناظر ثبت نام کردید.');
        } else {
            await ctx.answerCbQuery('⚠️ شما قبلا به عنوان ناظر ثبت نام کرده اید.');
        }
            
        await updateActiveListMessage(listId, ctx.telegram);
    } else if (action === 'start_game') {
        if (!isOwnerOrAdmin(userId)) {
            await ctx.answerCbQuery('⛔ فقط ادمین ها می‌توانند بازی را شروع کنند.');
            return;
        }

        // اطلاع‌رسانی به بازیکنان و ادمین‌ها در گروه‌ها
        const groups = loadJson(GROUP_FILE);
        const admins = loadJson(ADMIN_FILE);
        const adminIds = Object.keys(admins).map(id => parseInt(id));
        
        for (const groupId in groups) {
            try {
                // تگ کردن بازیکنان در دسته‌های 5 نفره
                const players = listData.players;
                for (let i = 0; i < players.length; i += 5) {
                    const batch = players.slice(i, i + 5);
                    const mentions = batch.map(p => `<a href='tg://user?id=${p.id}'>.</a>`).join(' ');
                    await ctx.telegram.sendMessage(
                        groupId,
                        `تگ بازیکنان:\n${mentions}`,
                        { parse_mode: 'HTML' }
                    );
                }
                
                // تگ کردن ادمین‌ها
                const allAdmins = [...adminIds, OWNER_ID];
                const uniqueAdmins = [...new Set(allAdmins)];
                for (let i = 0; i < uniqueAdmins.length; i += 5) {
                    const batch = uniqueAdmins.slice(i, i + 5);
                    const mentions = batch.map(id => `<a href='tg://user?id=${id}'>.</a>`).join(' ');
                    await ctx.telegram.sendMessage(
                        groupId,
                        `تگ ادمین‌ها:\n${mentions}`,
                        { parse_mode: 'HTML' }
                    );
                }
            } catch (error) {
                console.error(`Error notifying group ${groupId}:`, error);
            }
        }
            
        // حذف پیام لیست و ارسال پیام نهایی
        try {
            await ctx.telegram.deleteMessage(
                listData.channelId,
                listData.channelMessageId
            );
            await ctx.telegram.sendMessage(
                listData.channelId,
                "🎮 دوستان عزیز لابی زده شد تشریف بیارید"
            );
        } catch (error) {
            console.error('Error updating channel message:', error);
        }
            
        // پاک کردن لیست فعال
        delete activeList[listId];
        saveJson(ACTIVE_LIST_FILE, activeList);
        await ctx.answerCbQuery('✅ بازی شروع شد!');
    }
}

async function updateActiveListMessage(listId, telegram) {
    const activeList = loadJson(ACTIVE_LIST_FILE);
    const listData = activeList[listId];

    if (!listData || !listData.channelId) return;

    // آماده‌سازی لیست بازیکنان
    let playersText = listData.players.length > 0 ?
        listData.players.map((p, i) => `${i+1}) ${p.name}`).join('\n') :
        "هنوز بازیکنی ثبت نام نکرده است.";

    // آماده‌سازی لیست ناظران
    let observersText = listData.observers.length > 0 ?
        listData.observers.map(o => `👁️ ${o.name}`).join('\n') :
        "هنوز ناظری ثبت نام نکرده است.";

    // دریافت اطلاعات سازنده
    let creatorName = "Admin";
    if (isOwner(listData.creator)) {
        creatorName = "Owner";
    } else {
        const admins = loadJson(ADMIN_FILE);
        const adminInfo = admins[listData.creator.toString()];
        if (adminInfo) {
            creatorName = adminInfo.alias || "Admin";
        }
    }

    const messageText =
        `   🌟𝑱𝑼𝑹𝑨𝑺𝑺𝑰𝑪 𝑴𝑨𝑭𝑰𝑨 𝑮𝑹𝑶𝑼𝑷🌟\n\n` +
        `برای شرکت در لابی، وارد کانال✅ @jurassicmafia.شده و نام خود را ثبت کنید.\n` +
        `🎗سازنده لابی: ${creatorName}\n` +
        `⏰ساعت: ${listData.time.substring(0, 2)}:${listData.time.substring(2)}\n\n` +
        `🎭بازیکنان:\n${playersText}\n\n` +
        `🗿ناظران:\n${observersText}`;

    const keyboard = {
        inline_keyboard: [
            [{ text: '🎮 هستم', callback_data: `join_player:${listId}` }],
            [{ text: '👁️ ناظر', callback_data: `join_observer:${listId}` }],
            [{ text: '🚀 شروع', callback_data: `start_game:${listId}` }]
        ]
    };

    try {
        await telegram.editMessageText(
            listData.channelId,
            listData.channelMessageId,
            null,
            messageText,
            { 
                reply_markup: keyboard,
                parse_mode: 'Markdown'
            }
        );
    } catch (error) {
        console.error('Error updating active list:', error);
    }
}

// اجرای ربات
if (process.env.WEBHOOK_URL) {
    // حالت Webhook
    const domain = process.env.WEBHOOK_DOMAIN;
    const secretPath = `/telegraf/${BOT_TOKEN.split(':')[1]}`;
    const port = process.env.PORT || 10000;
    
    bot.launch({
        webhook: {
            domain: domain,
            port: port,
            hookPath: secretPath
        }
    }).then(() => {
        console.log(`Bot running in webhook mode on ${domain}${secretPath}`);
    });
} else {
    // حالت Polling
    bot.launch().then(() => {
        console.log('Bot running in polling mode');
    });
}

// مدیریت خطاها
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));

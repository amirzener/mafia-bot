const { Telegraf } = require('telegraf');
const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');

dotenv.config();

// تنظیمات اولیه
const BOT_TOKEN = process.env.BOT_TOKEN;
const OWNER_ID = parseInt(process.env.OWNER_ID);
const WEBHOOK_URL = process.env.WEBHOOK_URL;
const DATABASE_URL = process.env.DATABASE_URL;

const session = require('express-session');
const SequelizeStore = require('connect-session-sequelize')(session.Store);

const sequelize = new Sequelize(DATABASE_URL);

const sessionMiddleware = session({
  store: new SequelizeStore({
    db: sequelize,
    tableName: 'sessions',
    checkExpirationInterval: 15 * 60 * 1000, // هر 15 دقیقه بررسی انقضا
    expiration: 24 * 60 * 60 * 1000 // 1 روز
  }),
  secret: process.env.SESSION_SECRET || 'your-secret-key',
  resave: false,
  saveUninitialized: false,
  cookie: { secure: process.env.NODE_ENV === 'production' }
});

bot.use(sessionMiddleware);
// اتصال به PostgreSQL
const sequelize = new Sequelize(DATABASE_URL, {
  dialect: 'postgres',
  logging: false,
  dialectOptions: {
    ssl: process.env.DB_SSL === 'true' ? {
      require: true,
      rejectUnauthorized: false
    } : false
  }
});

// مدل‌های پایگاه داده
const initModels = async () => {
  const Admin = sequelize.define('admin', {
    user_id: { type: Sequelize.BIGINT, primaryKey: true },
    alias: { type: Sequelize.STRING },
    added_at: { type: Sequelize.DATE, defaultValue: Sequelize.NOW }
  });

  const Channel = sequelize.define('channel', {
    chat_id: { type: Sequelize.BIGINT, primaryKey: true },
    title: { type: Sequelize.STRING },
    username: { type: Sequelize.STRING },
    invite_link: { type: Sequelize.STRING },
    date_added: { type: Sequelize.DATE, defaultValue: Sequelize.NOW }
  });

  const Group = sequelize.define('group', {
    chat_id: { type: Sequelize.BIGINT, primaryKey: true },
    title: { type: Sequelize.STRING },
    username: { type: Sequelize.STRING },
    invite_link: { type: Sequelize.STRING },
    date_added: { type: Sequelize.DATE, defaultValue: Sequelize.NOW }
  });

  const ActiveList = sequelize.define('active_list', {
    list_id: { type: Sequelize.STRING, primaryKey: true },
    creator_id: { type: Sequelize.BIGINT },
    time: { type: Sequelize.STRING },
    players: { type: Sequelize.JSONB, defaultValue: [] },
    observers: { type: Sequelize.JSONB, defaultValue: [] },
    channel_id: { type: Sequelize.BIGINT },
    channel_message_id: { type: Sequelize.BIGINT },
    created_at: { type: Sequelize.DATE, defaultValue: Sequelize.NOW }
  });

  await sequelize.sync();

  return { Admin, Channel, Group, ActiveList };
};

// ایجاد ربات
const bot = new Telegraf(BOT_TOKEN);

// مسیر فایل‌های JSON
const ADMIN_FILE = "admin.json";
const CHANNEL_FILE = "channel.json";
const GROUP_FILE = "group.json";
const ACTIVE_LIST_FILE = "active_list.json";

// توابع کمکی برای مدیریت داده‌ها
async function loadJson(filePath, model) {
  try {
    // خواندن از فایل JSON
    const fileData = fs.existsSync(filePath) ? 
      JSON.parse(fs.readFileSync(filePath, 'utf8')) : {};
    
    // اگر مدلی ارائه شده، داده‌ها را در دیتابیس ذخیره می‌کنیم
    if (model) {
      for (const key in fileData) {
        try {
          await model.upsert({ ...fileData[key], 
            [model.primaryKeyAttribute]: key 
          });
        } catch (error) {
          console.error(`Error saving ${key} to database:`, error);
        }
      }
      
      // حذف فایل پس از انتقال داده‌ها به دیتابیس
      try {
        fs.unlinkSync(filePath);
      } catch (error) {
        console.error(`Error deleting ${filePath}:`, error);
      }
    }
    
    return fileData;
  } catch (error) {
    console.error(`Error loading ${filePath}:`, error);
    return {};
  }
}

async function saveToDatabase(model, key, data) {
  try {
    await model.upsert({ 
      [model.primaryKeyAttribute]: key,
      ...data
    });
    return true;
  } catch (error) {
    console.error(`Error saving to database (${model.name}):`, error);
    return false;
  }
}

async function deleteFromDatabase(model, key) {
  try {
    await model.destroy({ 
      where: { [model.primaryKeyAttribute]: key } 
    });
    return true;
  } catch (error) {
    console.error(`Error deleting from database (${model.name}):`, error);
    return false;
  }
}

async function getAllFromDatabase(model) {
  try {
    const results = await model.findAll();
    return results.reduce((acc, item) => {
      acc[item[model.primaryKeyAttribute]] = item.get({ plain: true });
      return acc;
    }, {});
  } catch (error) {
    console.error(`Error fetching all from database (${model.name}):`, error);
    return {};
  }
}

// توابع کمکی برای بررسی دسترسی
function isOwner(userId) {
  return userId === OWNER_ID;
}

async function isAdmin(userId, AdminModel) {
  if (isOwner(userId)) return true;
  const admin = await AdminModel.findByPk(userId.toString());
  return !!admin;
}

async function isOwnerOrAdmin(userId, AdminModel) {
  return isOwner(userId) || await isAdmin(userId, AdminModel);
}

function isValidTime(timeStr) {
  if (timeStr.length !== 4 || !/^\d+$/.test(timeStr)) return false;
  const hours = parseInt(timeStr.substring(0, 2));
  const minutes = parseInt(timeStr.substring(2));
  return hours >= 0 && hours < 24 && minutes >= 0 && minutes < 60;
}

// اجرای اصلی ربات
(async () => {
  try {
    // مقداردهی مدل‌ها
    const { Admin, Channel, Group, ActiveList } = await initModels();
    
    // بارگذاری داده‌های قدیمی از فایل‌های JSON و انتقال به دیتابیس
    await loadJson(ADMIN_FILE, Admin);
    await loadJson(CHANNEL_FILE, Channel);
    await loadJson(GROUP_FILE, Group);
    await loadJson(ACTIVE_LIST_FILE, ActiveList);
    
    // تنظیم session با Sequelize
    const sequelizeSession = new SequelizeSession(sequelize, {
      ttl: 86400 // زمان انقضای session (ثانیه)
    });
    bot.use(session());
    bot.use(sequelizeSession.middleware());

    // مدیریت اضافه شدن به گروه/کانال جدید
    bot.on('new_chat_members', async (ctx) => {
      const chat = ctx.chat;
      const botId = ctx.botInfo.id;
      
      if (ctx.message.new_chat_members.some(member => member.id === botId)) {
        const chatData = {
          title: chat.title,
          username: chat.username,
          invite_link: chat.invite_link,
          date_added: new Date()
        };
        
        if (chat.type === 'channel') {
          await saveToDatabase(Channel, chat.id, chatData);
          await ctx.telegram.sendMessage(
            OWNER_ID,
            `✅ به کانال اضافه شد:\n${chat.title}\nID: ${chat.id}`
          );
        } else if (chat.type === 'group' || chat.type === 'supergroup') {
          await saveToDatabase(Group, chat.id, chatData);
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
      if (!await isOwnerOrAdmin(ctx.from.id, Admin)) return;
      
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
        const listId = new Date().toISOString().replace(/[-:.]/g, '');
        const listData = {
          creator_id: ctx.from.id,
          time: timeStr,
          players: [],
          observers: []
        };
        
        await ActiveList.create({
          list_id: listId,
          ...listData
        });
            
        // ارسال پیام به کانال‌ها
        const channels = await getAllFromDatabase(Channel);
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
            await ActiveList.update({
              channel_id: channelId,
              channel_message_id: sentMsg.message_id
            }, {
              where: { list_id: listId }
            });
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
        await handleGameActions(ctx, Admin, ActiveList);
        return;
      }

      if (!isOwner(userId)) {
        await ctx.answerCbQuery('⛔ شما مجاز به استفاده از این پنل نیستید.');
        return;
      }

      if (data === 'show_groups') {
        await showGroupsMenu(ctx, Group);
      } else if (data === 'show_channels') {
        await showChannelsMenu(ctx, Channel);
      } else if (data === 'show_admins') {
        await showAdminsList(ctx, Admin);
      } else if (data === 'back_to_main') {
        await showMainMenu(ctx);
      } else if (data === 'close_panel') {
        await ctx.deleteMessage();
      } else if (data.startsWith('leave_chat:')) {
        const [, chatId, chatType] = data.split(':');
        try {
          await ctx.telegram.leaveChat(chatId);
          
          if (chatType === 'group') {
            await deleteFromDatabase(Group, chatId);
          } else {
            await deleteFromDatabase(Channel, chatId);
          }
          
          await ctx.answerCbQuery(`✅ از ${chatType} خارج شد.`);
          if (chatType === 'group') {
            await showGroupsMenu(ctx, Group);
          } else {
            await showChannelsMenu(ctx, Channel);
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

    async function showGroupsMenu(ctx, GroupModel) {
      const groups = await getAllFromDatabase(GroupModel);
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

    async function showChannelsMenu(ctx, ChannelModel) {
      const channels = await getAllFromDatabase(ChannelModel);
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

    async function showAdminsList(ctx, AdminModel) {
      const admins = await getAllFromDatabase(AdminModel);
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
    async function handleGameActions(ctx, AdminModel, ActiveListModel) {
      const data = ctx.callbackQuery.data;
      const userId = ctx.from.id;
      const [action, listId] = data.split(':');
      const listData = await ActiveListModel.findByPk(listId);

      if (!listData) {
        await ctx.answerCbQuery('❌ این لیست منقضی شده است.');
        return;
      }

      const listObj = listData.get({ plain: true });

      if (action === 'join_player') {
        const user = ctx.from;
        const username = `[${user.first_name}](tg://user?id=${user.id})`;
        
        if (!listObj.players.some(p => p.id === userId)) {
          const updatedPlayers = [...listObj.players, { id: userId, name: username }];
          await ActiveListModel.update(
            { players: updatedPlayers },
            { where: { list_id: listId } }
          );
          await ctx.answerCbQuery('✅ شما به عنوان بازیکن ثبت نام کردید.');
        } else {
          await ctx.answerCbQuery('⚠️ شما قبلا ثبت نام کرده اید.');
        }

        await updateActiveListMessage(listId, ctx.telegram, AdminModel, ActiveListModel);
      } else if (action === 'join_observer') {
        if (!await isOwnerOrAdmin(userId, AdminModel)) {
          await ctx.answerCbQuery('⛔ فقط ادمین ها می‌توانند ناظر باشند.');
          return;
        }

        if (listObj.observers.length >= 2) {
          await ctx.answerCbQuery('⚠️ حد مجاز ناظرین (2 نفر) تکمیل شده است.');
          return;
        }
            
        if (!listObj.observers.some(o => o.id === userId)) {
          const user = ctx.from;
          const username = `[${user.first_name}](tg://user?id=${user.id})`;
          const updatedObservers = [...listObj.observers, { id: userId, name: username }];
          await ActiveListModel.update(
            { observers: updatedObservers },
            { where: { list_id: listId } }
          );
          await ctx.answerCbQuery('✅ شما به عنوان ناظر ثبت نام کردید.');
        } else {
          await ctx.answerCbQuery('⚠️ شما قبلا به عنوان ناظر ثبت نام کرده اید.');
        }
            
        await updateActiveListMessage(listId, ctx.telegram, AdminModel, ActiveListModel);
      } else if (action === 'start_game') {
        if (!await isOwnerOrAdmin(userId, AdminModel)) {
          await ctx.answerCbQuery('⛔ فقط ادمین ها می‌توانند بازی را شروع کنند.');
          return;
        }

        // اطلاع‌رسانی به بازیکنان و ادمین‌ها در گروه‌ها
        const groups = await getAllFromDatabase(Group);
        const admins = await getAllFromDatabase(AdminModel);
        const adminIds = Object.keys(admins).map(id => parseInt(id));
        
        for (const groupId in groups) {
          try {
            // تگ کردن بازیکنان در دسته‌های 5 نفره
            const players = listObj.players;
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
            listObj.channel_id,
            listObj.channel_message_id
          );
          await ctx.telegram.sendMessage(
            listObj.channel_id,
            "🎮 دوستان عزیز لابی زده شد تشریف بیارید"
          );
        } catch (error) {
          console.error('Error updating channel message:', error);
        }
            
        // پاک کردن لیست فعال
        await ActiveListModel.destroy({ where: { list_id: listId } });
        await ctx.answerCbQuery('✅ بازی شروع شد!');
      }
    }

    async function updateActiveListMessage(listId, telegram, AdminModel, ActiveListModel) {
      const listData = await ActiveListModel.findByPk(listId);
      if (!listData || !listData.channel_id) return;

      const listObj = listData.get({ plain: true });

      // آماده‌سازی لیست بازیکنان
      let playersText = listObj.players.length > 0 ?
          listObj.players.map((p, i) => `${i+1}) ${p.name}`).join('\n') :
          "هنوز بازیکنی ثبت نام نکرده است.";

      // آماده‌سازی لیست ناظران
      let observersText = listObj.observers.length > 0 ?
          listObj.observers.map(o => `👁️ ${o.name}`).join('\n') :
          "هنوز ناظری ثبت نام نکرده است.";

      // دریافت اطلاعات سازنده
      let creatorName = "Admin";
      if (isOwner(listObj.creator_id)) {
        creatorName = "Owner";
      } else {
        const admin = await AdminModel.findByPk(listObj.creator_id.toString());
        if (admin) {
          creatorName = admin.alias || "Admin";
        }
      }

      const messageText =
          `   🌟𝑱𝑼𝑹𝑨𝑺𝑺𝑰𝑪 𝑴𝑨𝑭𝑰𝑨 𝑮𝑹𝑶𝑼𝑷🌟\n\n` +
          `برای شرکت در لابی، وارد کانال✅ @jurassicmafia.شده و نام خود را ثبت کنید.\n` +
          `🎗سازنده لابی: ${creatorName}\n` +
          `⏰ساعت: ${listObj.time.substring(0, 2)}:${listObj.time.substring(2)}\n\n` +
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
          listObj.channel_id,
          listObj.channel_message_id,
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

  } catch (error) {
    console.error('Error initializing bot:', error);
    process.exit(1);
  }
})();

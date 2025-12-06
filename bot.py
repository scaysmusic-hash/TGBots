import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from dotenv import load_dotenv
from database import Database
from PIL import Image
import io

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_TELEGRAM_ID = int(os.getenv("OWNER_TELEGRAM_ID", 0)) # ID владельца для инициализации

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
DB = Database()
STAR_TO_RUB_RATE = 1 # 1 Звездочка = 1 Рубль
WITHDRAWAL_COMMISSION_PERCENT = 15 # Комиссия за вывод 15%

# Состояния для ConversationHandler
(
    REGISTER_USERNAME,
    REPLENISH_AMOUNT,
    REPLENISH_SCREENSHOT,
    WITHDRAW_AMOUNT,
    WITHDRAW_REQUISITES,
    CREATE_LISTING_TITLE,
    CREATE_LISTING_PHOTO,
    CREATE_LISTING_PRICE,
    CREATE_LISTING_TYPE,
    CREATE_PROMO_CODE,
    CREATE_PROMO_DISCOUNT,
    CREATE_CONTEST_TITLE,
    CREATE_CONTEST_DESC,
    CREATE_CONTEST_PRIZE,
    APPLICATION_NAME,
    APPLICATION_COMPANY,
    APPLICATION_PRODUCTS,
    APPLICATION_ABOUT,
    APPLICATION_EXPERIENCE,
    ADMIN_ADD_REQUISITE_NAME,
    ADMIN_ADD_REQUISITE_DETAILS,
    ADMIN_POST_CONTENT,
    ADMIN_CHANGE_PRICE,
    ADMIN_TRANSFER_TOKENS_AMOUNT,
    ADMIN_TRANSFER_TOKENS_TARGET,
    ADMIN_BLOCK_USER,
    ADMIN_FREEZE_USER,
    ADMIN_CHANGE_ROLE,
    ADMIN_COMPLAINT_REASON,
    ADMIN_COMPLAINT_RATING
) = range(31)

# ===== КЛАВИАТУРЫ =====

def get_main_keyboard(role):
    """Возвращает основную клавиатуру в зависимости от роли"""
    if role == 'Владелец':
        keyboard = [
            ["👤 Профиль", "💰 Рынок"],
            ["➕ Создать объявление", "📦 Объявления"],
            ["👥 Пользователи", "⭐ Токены"],
            ["⬆️ Пополнить баланс", "⬇️ Вывести баланс"],
            ["⚠️ Жалобы", "⚙️ Настройки"]
        ]
    elif role == 'Администратор':
        keyboard = [
            ["👤 Профиль", "💰 Рынок"],
            ["📦 Объявления", "👥 Пользователи"],
            ["⬆️ Пополнить баланс", "⬇️ Вывести баланс"],
            ["⚠️ Жалобы"]
        ]
    elif role == 'Предприниматель':
        keyboard = [
            ["👤 Профиль", "💰 Рынок"],
            ["➕ Создать объявление", "🏷️ Создать промокод"],
            ["⬆️ Пополнить баланс", "⬇️ Вывести баланс"],
            ["⚠️ Пожаловаться"]
        ]
    else: # Покупатель
        keyboard = [
            ["👤 Профиль", "💰 Рынок"],
            ["🏷️ Промокод", "🚀 Получить повышение"],
            ["⬆️ Пополнить баланс", "⬇️ Вывести баланс"],
            ["⚠️ Пожаловаться"]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_users_keyboard():
    """Клавиатура для управления пользователями"""
    keyboard = [
        ["Блокировка/Разблокировка", "Заморозка/Разморозка"],
        ["Изменить роль", "Начислить/Списать ⭐"],
        ["Назад в Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_owner_tokens_keyboard():
    """Клавиатура для управления токенами (Владелец)"""
    keyboard = [
        ["Начислить/Списать ⭐", "Управление реквизитами"],
        ["Рассылка", "Назад в Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_market_keyboard():
    """Клавиатура для рынка"""
    keyboard = [
        ["Поиск по названию", "Назад в Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== СТАРТ И РЕГИСТРАЦИЯ =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало диалога, проверка регистрации"""
    user = update.effective_user
    db_user = DB.get_user(user.id)

    if db_user:
        # Пользователь зарегистрирован
        role = db_user[4]
        await update.message.reply_text(
            f"С возвращением, {db_user[2]}! Ваша роль: {role}.",
            reply_markup=get_main_keyboard(role)
        )
        return ConversationHandler.END
    else:
        # Пользователь не зарегистрирован, запрашиваем никнейм
        await update.message.reply_text(
            "Добро пожаловать на Рынок! Для регистрации придумайте себе уникальный никнейм (только латинские буквы и цифры):",
            reply_markup=ReplyKeyboardRemove()
        )
        return REGISTER_USERNAME

async def register_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка введенного никнейма"""
    user = update.effective_user
    username = update.message.text.strip()

    if not username.isalnum() or len(username) < 3 or len(username) > 15:
        await update.message.reply_text("Никнейм должен содержать только латинские буквы и цифры, быть от 3 до 15 символов. Попробуйте еще раз:")
        return REGISTER_USERNAME

    if DB.get_user_by_username(username):
        await update.message.reply_text("Этот никнейм уже занят. Попробуйте другой:")
        return REGISTER_USERNAME

    # Регистрация
    DB.add_user(user.id, user.first_name, username)
    
    # Инициализация Владельца, если это первый запуск
    if user.id == OWNER_TELEGRAM_ID:
        # Проверяем, не был ли он уже инициализирован как Владелец
        existing_user = DB.get_user(user.id)
        if existing_user and existing_user[4] != 'Владелец':
            DB.update_role(user.id, 'Владелец')
        elif not existing_user:
            # Если по какой-то причине не добавился, добавляем и сразу ставим Владельцем
            DB.add_user(user.id, user.first_name, username)
            DB.update_role(user.id, 'Владелец')
        
    db_user = DB.get_user(user.id)
    role = db_user[4]
    
    await update.message.reply_text(
        f"Поздравляем, {username}! Вы успешно зарегистрированы. Ваша роль: {role}.",
        reply_markup=get_main_keyboard(role)
    )
    return ConversationHandler.END

# ===== ОСНОВНЫЕ ФУНКЦИИ =====

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображение профиля пользователя"""
    user = update.effective_user
    db_user = DB.get_user(user.id)
    
    if not db_user:
        await update.message.reply_text("Пожалуйста, начните с команды /start для регистрации.")
        return
        
    (
        user_id, telegram_id, username, first_name, role, balance, frozen_balance, 
        rating, status, complaints_count, is_blocked, is_frozen, is_admin, is_owner, 
        company_name, experience, created_at
    ) = db_user
    
    # Количество объявлений
    listings = DB.get_user_listings(telegram_id)
    listing_count = len(listings) if role in ('Предприниматель', 'Администратор', 'Владелец') else 0
    
    message = (
        f"👤 **Профиль: {username}**\n"
        f"**Роль:** {role}\n"
        f"**Рейтинг:** {rating}\n"
        f"**Баланс:** {balance} ⭐\n"
        f"**Заморожено:** {frozen_balance} ⭐\n"
        f"**Статус аккаунта:** {status}\n"
    )
    
    if listing_count > 0:
        message += f"**Опубликовано объявлений:** {listing_count}\n"
        
    if is_blocked:
        message += "⚠️ **АККАУНТ ЗАБЛОКИРОВАН ВЛАДЕЛЬЦЕМ**\n"
    if is_frozen:
        message += "❄️ **АККАУНТ ЗАМОРОЖЕН (токены недоступны)**\n"
        
    await update.message.reply_text(message, parse_mode='Markdown')

async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображение рынка и активных объявлений"""
    listings = DB.get_all_active_listings()
    
    if not listings:
        await update.message.reply_text("На данный момент на Рынке нет активных объявлений.",
                                        reply_markup=get_market_keyboard())
        return
        
    message = "💰 **Актуальные объявления на Рынке:**\n\n"
    
    # Выводим первые 5 объявлений
    for listing in listings[:5]:
        (
            listing_id, title, description, price, is_service, photo_path, 
            seller_name, seller_username, seller_rating
        ) = listing
        
        message += (
            f"**{title}** (ID: {listing_id})\n"
            f"**Цена:** {price} ⭐\n"
            f"**Тип:** {'Услуга' if is_service else 'Товар'}\n"
            f"**Продавец:** {seller_username} (Рейтинг: {seller_rating})\n"
            f"_{description[:50]}..._\n\n"
        )
        
        keyboard = [[InlineKeyboardButton("Купить/Заказать", callback_data=f"buy_listing_{listing_id}")]]
        
        await update.message.reply_photo(
            photo=open(photo_path, 'rb'),
            caption=message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    if len(listings) > 5:
        await update.message.reply_text(f"И еще {len(listings) - 5} объявлений. Используйте поиск или пролистайте.",
                                        reply_markup=get_market_keyboard())
    else:
        await update.message.reply_text("Конец списка объявлений.", reply_markup=get_market_keyboard())

async def buy_listing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки 'Купить/Заказать'"""
    query = update.callback_query
    await query.answer()
    
    listing_id = int(query.data.split('_')[-1])
    listing = DB.get_listing_by_id(listing_id)
    
    if not listing:
        await query.edit_message_caption("❌ Объявление не найдено.")
        return
        
    listing_id, title, description, price, is_service, photo_path, seller_telegram_id, seller_username, seller_rating = listing
    
    # Проверка, что не покупает сам у себя
    if query.from_user.id == seller_telegram_id:
        await query.edit_message_caption("❌ Вы не можете купить собственное объявление.")
        return
        
    # Создание безопасной сделки
    success, result = DB.create_safe_deal(query.from_user.id, listing_id, price)
    
    if success:
        deal_id = result
        
        # Уведомление покупателя
        await query.edit_message_caption(
            f"✅ **Сделка начата!**\n"
            f"**{title}** - {price} ⭐\n"
            f"Средства ({price} ⭐) заморожены на вашем счету.\n"
            f"**ID Сделки:** {deal_id}\n\n"
            f"Свяжитесь с продавцом @{seller_username} для получения товара/услуги.\n"
            f"После получения нажмите 'Завершить сделку'."
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Завершить сделку", callback_data=f"complete_deal_{deal_id}")],
            [InlineKeyboardButton("⚠️ Начать арбитраж", callback_data=f"arbitration_start_{deal_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Управление сделкой:",
            reply_markup=reply_markup
        )
        
        # Уведомление продавца
        await context.bot.send_message(
            chat_id=seller_telegram_id,
            text=(
                f"🔔 **НОВАЯ СДЕЛКА!**\n"
                f"**Объявление:** {title}\n"
                f"**Сумма:** {price} ⭐\n"
                f"**Покупатель:** @{query.from_user.username}\n"
                f"**ID Сделки:** {deal_id}\n\n"
                f"Средства заморожены на счету покупателя. Выполните заказ."
            ),
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_caption(f"❌ Ошибка при начале сделки: {result}")

async def complete_deal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка завершения сделки"""
    query = update.callback_query
    await query.answer()
    
    deal_id = int(query.data.split('_')[-1])
    
    success, message = DB.complete_safe_deal(deal_id, query.from_user.id)
    
    if success:
        deal = DB.get_safe_deal(deal_id)
        seller_telegram_id = DB.get_user_by_id(deal[2])[1]
        
        await query.edit_message_text(f"✅ **Сделка ID {deal_id} успешно завершена!**\n{message}")
        
        # Уведомление продавца
        await context.bot.send_message(
            chat_id=seller_telegram_id,
            text=f"✅ **Сделка ID {deal_id} завершена!** Средства ({deal[4]} ⭐) начислены на ваш баланс."
        )
    else:
        await query.edit_message_text(f"❌ Ошибка при завершении сделки: {message}")

async def arbitration_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало арбитража - запрос причины"""
    query = update.callback_query
    await query.answer()
    
    deal_id = int(query.data.split('_')[-1])
    context.user_data['arbitration_deal_id'] = deal_id
    
    await query.edit_message_text(
        f"⚠️ **Арбитраж по сделке ID {deal_id}**\n"
        f"Пожалуйста, опишите причину, по которой вы хотите начать арбитраж (например, 'Товар не соответствует описанию', 'Продавец не выходит на связь')."
    )
    return ADMIN_COMPLAINT_REASON # Используем то же состояние для ввода причины

async def arbitration_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка причины арбитража и его начало"""
    reason = update.message.text.strip()
    deal_id = context.user_data.pop('arbitration_deal_id')
    
    success, message = DB.start_arbitration(deal_id, update.effective_user.id, reason)
    
    if success:
        await update.message.reply_text(
            f"✅ **Арбитраж по сделке ID {deal_id} начат!**\n"
            f"Ваша заявка отправлена Администраторам на рассмотрение."
        )
        
        # Уведомление Администраторов (Владельца)
        owner_user = DB.get_user(OWNER_TELEGRAM_ID)
        if owner_user:
            deal = DB.get_safe_deal(deal_id)
            buyer_telegram_id = DB.get_user_by_id(deal[1])[1]
            seller_telegram_id = DB.get_user_by_id(deal[2])[1]
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Победитель: Покупатель", callback_data=f"arb_resolve_{deal_id}_{buyer_telegram_id}"),
                    InlineKeyboardButton("❌ Победитель: Продавец", callback_data=f"arb_resolve_{deal_id}_{seller_telegram_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=OWNER_TELEGRAM_ID,
                text=(
                    f"🚨 **НОВЫЙ АРБИТРАЖ!**\n"
                    f"**ID Сделки:** {deal_id}\n"
                    f"**Покупатель:** @{DB.get_user(buyer_telegram_id)[2]}\n"
                    f"**Продавец:** @{DB.get_user(seller_telegram_id)[2]}\n"
                    f"**Сумма:** {deal[4]} ⭐\n"
                    f"**Причина:** {reason}"
                ),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(f"❌ Ошибка при начале арбитража: {message}")
        
    return ConversationHandler.END

async def complaint_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало подачи жалобы"""
    await update.message.reply_text("Введите **никнейм** пользователя, на которого вы хотите пожаловаться:")
    return ADMIN_BLOCK_USER # Используем то же состояние для ввода никнейма

async def complaint_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка никнейма цели жалобы"""
    target_username = update.message.text.strip()
    target_user = DB.get_user_by_username(target_username)
    
    if not target_user:
        await update.message.reply_text("Пользователь с таким никнеймом не найден. Попробуйте еще раз:")
        return ADMIN_BLOCK_USER
        
    context.user_data['complaint_target_id'] = target_user[1] # telegram_id
    
    await update.message.reply_text("Опишите **причину жалобы**:")
    return ADMIN_COMPLAINT_REASON

async def complaint_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка причины жалобы и ее сохранение"""
    reason = update.message.text.strip()
    target_telegram_id = context.user_data.pop('complaint_target_id')
    
    success, result = DB.add_complaint(update.effective_user.id, target_telegram_id, reason)
    
    if success:
        complaint_id = result
        await update.message.reply_text(f"✅ Ваша жалоба (ID: {complaint_id}) отправлена Администраторам на рассмотрение.")
        
        # Уведомление Администраторов (Владельца)
        owner_user = DB.get_user(OWNER_TELEGRAM_ID)
        if owner_user:
            target_user = DB.get_user(target_telegram_id)
            
            keyboard = [
                [InlineKeyboardButton("Рассмотреть жалобу", callback_data=f"complaint_review_{complaint_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=OWNER_TELEGRAM_ID,
                text=(
                    f"🚨 **НОВАЯ ЖАЛОБА!**\n"
                    f"**ID Жалобы:** {complaint_id}\n"
                    f"**На кого:** @{target_user[2]}\n"
                    f"**От кого:** @{update.effective_user.username}\n"
                    f"**Причина:** {reason}"
                ),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(f"❌ Ошибка при подаче жалобы: {result}")
        
    return ConversationHandler.END

async def complaint_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало рассмотрения жалобы"""
    query = update.callback_query
    await query.answer()
    
    complaint_id = int(query.data.split('_')[-1])
    
    # Здесь нужно получить детали жалобы, но пока просто переходим к решению
    context.user_data['review_complaint_id'] = complaint_id
    
    await query.edit_message_text(
        f"**Рассмотрение жалобы ID {complaint_id}**\n"
        f"Введите **изменение рейтинга** для пользователя (например, `-5` для снижения на 5, `+0` для без изменений):"
    )
    return ADMIN_COMPLAINT_RATING

async def complaint_rating_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка изменения рейтинга"""
    try:
        rating_change = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное целое число для изменения рейтинга.")
        return ADMIN_COMPLAINT_RATING
        
    context.user_data['rating_change'] = rating_change
    
    keyboard = [
        [InlineKeyboardButton("Оставить статус без изменений", callback_data="status_change_None")],
        [InlineKeyboardButton("Сменить на 'Надежный'", callback_data="status_change_Надежный")],
        [InlineKeyboardButton("Сменить на 'Подозрительный'", callback_data="status_change_Подозрительный")],
        [InlineKeyboardButton("Сменить на 'Критический'", callback_data="status_change_Критический")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Выберите **новый статус** аккаунта:", reply_markup=reply_markup)
    return ConversationHandler.END # Переход в CallbackQueryHandler

async def complaint_status_change_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка изменения статуса и разрешение жалобы"""
    query = update.callback_query
    await query.answer()
    
    new_status = query.data.split('_')[-1]
    if new_status == 'None':
        new_status = None
        
    complaint_id = context.user_data.pop('review_complaint_id')
    rating_change = context.user_data.pop('rating_change')
    
    success = DB.resolve_complaint(complaint_id, query.from_user.id, rating_change, new_status)
    
    if success:
        await query.edit_message_text(
            f"✅ **Жалоба ID {complaint_id} разрешена!**\n"
            f"Изменение рейтинга: {rating_change}\n"
            f"Новый статус: {new_status if new_status else 'Без изменений'}"
        )
    else:
        await query.edit_message_text(f"❌ Ошибка при разрешении жалобы ID {complaint_id}.")

# Добавление обработчиков в main()
# ...
# ConversationHandler для жалоб
    complaint_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^⚠️ Пожаловаться$"), complaint_start)],
        states={
            ADMIN_BLOCK_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_target)],
            ADMIN_COMPLAINT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_reason)],
        },
        fallbacks=[MessageHandler(filters.Regex("^⚠️ Пожаловаться$"), complaint_start)],
    )
    application.add_handler(complaint_handler)

    # ConversationHandler для рассмотрения жалоб
    complaint_review_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(complaint_review_callback, pattern=r'^complaint_review_\d+$')],
        states={
            ADMIN_COMPLAINT_RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_rating_change)],
        },
        fallbacks=[CallbackQueryHandler(complaint_review_callback, pattern=r'^complaint_review_\d+$')],
    )
    application.add_handler(complaint_review_handler)

    # CallbackQueryHandler для смены статуса
    application.add_handler(CallbackQueryHandler(complaint_status_change_callback, pattern=r'^status_change_.*$'))

async def arbitration_resolve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Разрешение арбитража администратором"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    deal_id = int(data[2])
    winner_telegram_id = int(data[3])
    
    success, message = DB.resolve_arbitration(deal_id, winner_telegram_id, query.from_user.id)
    
    if success:
        deal = DB.get_safe_deal(deal_id)
        buyer_telegram_id = DB.get_user_by_id(deal[1])[1]
        seller_telegram_id = DB.get_user_by_id(deal[2])[1]
        
        winner_username = DB.get_user(winner_telegram_id)[2]
        
        await query.edit_message_text(
            query.message.text + f"\n\n✅ **АРБИТРАЖ РАЗРЕШЕН.** Победитель: @{winner_username}"
        )
        
        # Уведомление участников
        await context.bot.send_message(
            chat_id=buyer_telegram_id,
            text=f"✅ **Арбитраж по сделке ID {deal_id} разрешен!** Проверьте ваш баланс."
        )
        await context.bot.send_message(
            chat_id=seller_telegram_id,
            text=f"✅ **Арбитраж по сделке ID {deal_id} разрешен!** Проверьте ваш баланс."
        )
    else:
        await query.edit_message_text(
            query.message.text + f"\n\n❌ **ОШИБКА РАЗРЕШЕНИЯ:** {message}"
        )

# ===== ФУНКЦИИ ПОПОЛНЕНИЯ =====

async def replenish_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса пополнения баланса"""
    db_user = DB.get_user(update.effective_user.id)
    if not db_user:
        await update.message.reply_text("Пожалуйста, начните с команды /start для регистрации.")
        return ConversationHandler.END
        
    await update.message.reply_text(
        f"Введите сумму в рублях, на которую вы хотите пополнить баланс.\n"
        f"Курс: 1 ⭐ = {STAR_TO_RUB_RATE} ₽\n"
        f"Например, если вы введете 100, вы получите 100 ⭐."
    )
    return REPLENISH_AMOUNT

async def replenish_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка введенной суммы пополнения"""
    try:
        rub_amount = int(update.message.text)
        if rub_amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректную положительную сумму в рублях.")
        return REPLENISH_AMOUNT
        
    stars_amount = rub_amount * STAR_TO_RUB_RATE
    
    context.user_data['rub_amount'] = rub_amount
    context.user_data['stars_amount'] = stars_amount
    
    requisites = DB.get_active_requisites()
    if not requisites:
        await update.message.reply_text("Владелец еще не добавил реквизиты для пополнения. Попробуйте позже.")
        return ConversationHandler.END
        
    keyboard = [[InlineKeyboardButton(req[1], callback_data=f"replenish_req_{req[0]}")] for req in requisites]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Вы хотите пополнить на **{rub_amount} ₽**, что составит **{stars_amount} ⭐**.\n"
        f"Выберите способ пополнения:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return ConversationHandler.END # Переход в CallbackQueryHandler

async def replenish_requisite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отображение реквизитов и запрос скриншота"""
    query = update.callback_query
    await query.answer()
    
    requisite_id = int(query.data.split('_')[-1])
    
    # В идеале нужно получить реквизиты по ID, но для простоты возьмем из списка активных
    requisites = DB.get_active_requisites()
    selected_req = next((req for req in requisites if req[0] == requisite_id), None)
    
    if not selected_req:
        await query.edit_message_text("Ошибка: Реквизиты не найдены.")
        return ConversationHandler.END
        
    context.user_data['requisite_id'] = requisite_id
    
    message = (
        f"**Реквизиты для пополнения ({selected_req[1]}):**\n"
        f"```\n{selected_req[2]}\n```\n\n"
        f"Переведите **{context.user_data['rub_amount']} ₽** на указанные реквизиты.\n"
        f"После оплаты **прикрепите скриншот** и нажмите кнопку 'Я пополнил'."
    )
    
    keyboard = [[InlineKeyboardButton("✅ Я пополнил", callback_data="replenish_screenshot")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    return ConversationHandler.END # Переход в CallbackQueryHandler

async def replenish_screenshot_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрос скриншота после нажатия кнопки 'Я пополнил'"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Пожалуйста, **прикрепите скриншот** оплаты в следующем сообщении.\n"
        "Это необходимо для подтверждения перевода Владельцем."
    )
    return REPLENISH_SCREENSHOT

async def replenish_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка скриншота и создание заявки"""
    user = update.effective_user
    
    if not update.message.photo:
        await update.message.reply_text("Пожалуйста, отправьте именно фотографию (скриншот) оплаты.")
        return REPLENISH_SCREENSHOT
        
    photo_file = await update.message.photo[-1].get_file()
    
    # Сохранение скриншота локально
    photo_path = f"replenishment_screenshots/{user.id}_{photo_file.file_unique_id}.jpg"
    os.makedirs("replenishment_screenshots", exist_ok=True)
    await photo_file.download_to_drive(photo_path)
    
    db_user = DB.get_user(user.id)
    user_id = db_user[0]
    
    request_id = DB.create_replenishment_request(
        user_id, 
        context.user_data['rub_amount'], 
        context.user_data['stars_amount'], 
        photo_path
    )
    
    # Уведомление Владельца
    owner_user = DB.get_user(OWNER_TELEGRAM_ID)
    if owner_user:
        keyboard = [
            [
                InlineKeyboardButton("✅ Оплата поступила", callback_data=f"replenish_confirm_{request_id}"),
                InlineKeyboardButton("❌ Оплата не поступила", callback_data=f"replenish_reject_{request_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_photo(
            chat_id=OWNER_TELEGRAM_ID,
            photo=open(photo_path, 'rb'),
            caption=(
                f"🔔 **НОВАЯ ЗАЯВКА НА ПОПОЛНЕНИЕ**\n"
                f"**ID Заявки:** {request_id}\n"
                f"**Пользователь:** @{db_user[2]} ({db_user[3]})\n"
                f"**Сумма:** {context.user_data['rub_amount']} ₽ -> {context.user_data['stars_amount']} ⭐\n"
                f"**Скриншот оплаты прикреплен.**"
            ),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    await update.message.reply_text(
        "✅ Ваша заявка на пополнение отправлена Владельцу на проверку. "
        "Как только оплата будет подтверждена, звезды будут начислены на ваш баланс."
    )
    
    # Очистка user_data
    context.user_data.clear()
    return ConversationHandler.END

# ===== ФУНКЦИИ ВЫВОДА =====

async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса вывода баланса"""
    db_user = DB.get_user(update.effective_user.id)
    if not db_user:
        await update.message.reply_text("Пожалуйста, начните с команды /start для регистрации.")
        return ConversationHandler.END
        
    balance = db_user[5]
    if balance == 0:
        await update.message.reply_text("Ваш баланс пуст. Вывод невозможен.")
        return ConversationHandler.END
        
    message = (
        f"⚠️ **ВНИМАНИЕ!**\n"
        f"Ваш текущий баланс: **{balance} ⭐**.\n"
        f"За вывод средств взимается комиссия **{WITHDRAWAL_COMMISSION_PERCENT}%**.\n"
        f"Курс: 1 ⭐ = {STAR_TO_RUB_RATE} ₽.\n\n"
        f"Нажмите 'Продолжить', чтобы ввести сумму."
    )
    
    keyboard = [[InlineKeyboardButton("➡️ Продолжить", callback_data="withdraw_continue")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    return ConversationHandler.END # Переход в CallbackQueryHandler

async def withdraw_amount_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрос суммы вывода"""
    query = update.callback_query
    await query.answer()
    
    db_user = DB.get_user(query.from_user.id)
    balance = db_user[5]
    
    await query.edit_message_text(
        f"Введите сумму в звездах (⭐), которую вы хотите вывести.\n"
        f"Ваш баланс: **{balance} ⭐**."
    )
    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка введенной суммы вывода"""
    db_user = DB.get_user(update.effective_user.id)
    balance = db_user[5]
    
    try:
        stars_amount = int(update.message.text)
        if stars_amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректную положительную сумму в звездах.")
        return WITHDRAW_AMOUNT
        
    if stars_amount > balance:
        await update.message.reply_text(f"Недостаточно средств. Ваш баланс: {balance} ⭐. Попробуйте еще раз:")
        return WITHDRAW_AMOUNT
        
    # Расчет комиссии
    commission = stars_amount * WITHDRAWAL_COMMISSION_PERCENT / 100
    rub_amount = (stars_amount - commission) * STAR_TO_RUB_RATE
    
    context.user_data['stars_amount'] = stars_amount
    context.user_data['rub_amount'] = rub_amount
    
    message = (
        f"**Заявка на вывод:**\n"
        f"**Сумма в ⭐:** {stars_amount} ⭐\n"
        f"**Комиссия ({WITHDRAWAL_COMMISSION_PERCENT}%):** {commission:.2f} ⭐\n"
        f"**Сумма к выплате в ₽:** {rub_amount:.2f} ₽\n\n"
        f"Нажмите 'Вывести' и введите реквизиты."
    )
    
    keyboard = [[InlineKeyboardButton("➡️ Вывести", callback_data="withdraw_requisites")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    return ConversationHandler.END # Переход в CallbackQueryHandler

async def withdraw_requisites_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрос реквизитов для вывода"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Пожалуйста, введите ваши реквизиты для вывода в формате:\n"
        "`89005006767 - Сбербанк ( Юлия )`"
    )
    return WITHDRAW_REQUISITES

async def withdraw_requisites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка реквизитов и создание заявки"""
    user = update.effective_user
    requisites = update.message.text.strip()
    
    db_user = DB.get_user(user.id)
    user_id = db_user[0]
    
    # Списываем звезды с баланса пользователя сразу
    DB.update_balance(user.id, -context.user_data['stars_amount'])
    
    request_id = DB.create_withdrawal_request(
        user_id, 
        context.user_data['stars_amount'], 
        context.user_data['rub_amount'], 
        requisites
    )
    
    # Уведомление Владельца
    owner_user = DB.get_user(OWNER_TELEGRAM_ID)
    if owner_user:
        keyboard = [
            [
                InlineKeyboardButton("✅ Вывод успешен", callback_data=f"withdraw_confirm_{request_id}"),
                InlineKeyboardButton("❌ Отклонить вывод", callback_data=f"withdraw_reject_{request_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=OWNER_TELEGRAM_ID,
            text=(
                f"🔔 **НОВАЯ ЗАЯВКА НА ВЫВОД**\n"
                f"**ID Заявки:** {request_id}\n"
                f"**Пользователь:** @{db_user[2]} ({db_user[3]})\n"
                f"**Сумма в ⭐:** {context.user_data['stars_amount']} ⭐\n"
                f"**Сумма к выплате в ₽:** {context.user_data['rub_amount']:.2f} ₽\n"
                f"**Реквизиты:**\n`{requisites}`"
            ),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    await update.message.reply_text(
        "✅ Ваша заявка на вывод отправлена Владельцу. "
        "Средства в звездах списаны с вашего баланса. Ожидайте перевода."
    )
    
    # Очистка user_data
    context.user_data.clear()
    return ConversationHandler.END

# ===== АДМИН-ФУНКЦИИ (ОБРАБОТКА ЗАЯВОК) =====

async def admin_replenish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения/отклонения пополнения"""
    query = update.callback_query
    await query.answer()
    
    action, request_id = query.data.split('_')[-2:]
    request_id = int(request_id)
    admin_id = query.from_user.id
    
    if action == 'confirm':
        success, user_telegram_id_or_error, stars_amount = DB.confirm_replenishment(request_id, admin_id)
        if success:
            await context.bot.send_message(
                chat_id=user_telegram_id_or_error,
                text=f"✅ **Пополнение подтверждено!** На ваш баланс начислено **{stars_amount} ⭐**."
            )
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n✅ **ПОДТВЕРЖДЕНО ВЛАДЕЛЬЦЕМ**",
                reply_markup=None,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_caption(
                caption=query.message.caption + f"\n\n❌ **ОШИБКА:** {user_telegram_id_or_error}",
                reply_markup=None,
                parse_mode='Markdown'
            )
    elif action == 'reject':
        success, user_telegram_id_or_error = DB.reject_replenishment(request_id, admin_id)
        if success:
            await context.bot.send_message(
                chat_id=user_telegram_id_or_error,
                text="❌ **Пополнение отклонено.** Владелец не получил оплату. Пожалуйста, свяжитесь с поддержкой."
            )
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ **ОТКЛОНЕНО ВЛАДЕЛЬЦЕМ**",
                reply_markup=None,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_caption(
                caption=query.message.caption + f"\n\n❌ **ОШИБКА:** {user_telegram_id_or_error}",
                reply_markup=None,
                parse_mode='Markdown'
            )

async def owner_withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения/отклонения вывода"""
    query = update.callback_query
    await query.answer()
    
    action, request_id = query.data.split('_')[-2:]
    request_id = int(request_id)
    owner_id = query.from_user.id
    
    if action == 'confirm':
        success, user_telegram_id_or_error = DB.confirm_withdrawal(request_id, owner_id)
        if success:
            await context.bot.send_message(
                chat_id=user_telegram_id_or_error,
                text="✅ **Вывод успешен!** Средства перечислены на ваши реквизиты."
            )
            await query.edit_message_text(
                text=query.message.text + "\n\n✅ **ВЫВОД УСПЕШЕН**",
                reply_markup=None,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                text=query.message.text + f"\n\n❌ **ОШИБКА:** {user_telegram_id_or_error}",
                reply_markup=None,
                parse_mode='Markdown'
            )
    elif action == 'reject':
        # При отклонении нужно вернуть токены пользователю
        request = DB.get_withdrawal_request(request_id)
        if request:
            user_id, stars_amount = request[1], request[3]
            # Получаем telegram_id пользователя
            user_telegram_id = DB.get_user_by_id(user_id)[1]
            DB.update_balance(user_telegram_id, stars_amount) # Возвращаем токены
            
            success, user_telegram_id_or_error = DB.reject_withdrawal(request_id, owner_id)
            if success:
                await context.bot.send_message(
                    chat_id=user_telegram_id_or_error,
                    text=f"❌ **Вывод отклонен.** {stars_amount} ⭐ возвращены на ваш баланс."
                )
                await query.edit_message_text(
                    text=query.message.text + "\n\n❌ **ОТКЛОНЕНО ВЛАДЕЛЬЦЕМ**",
                    reply_markup=None,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    text=query.message.text + f"\n\n❌ **ОШИБКА:** {user_telegram_id_or_error}",
                    reply_markup=None,
                    parse_mode='Markdown'
                )
        else:
            await query.edit_message_text(
                text=query.message.text + "\n\n❌ **ОШИБКА:** Заявка не найдена.",
                reply_markup=None,
                parse_mode='Markdown'
            )

# ===== ФУНКЦИИ ПРЕДПРИНИМАТЕЛЯ: ОБЪЯВЛЕНИЯ =====

async def create_listing_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало создания объявления"""
    user = update.effective_user
    if not DB.is_entrepreneur(user.id):
        await update.message.reply_text("У вас нет прав для создания объявлений.")
        return ConversationHandler.END
        
    await update.message.reply_text("Введите **Название** вашего товара или услуги:")
    return CREATE_LISTING_TITLE

async def create_listing_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка названия объявления"""
    context.user_data['listing_title'] = update.message.text.strip()
    await update.message.reply_text("Теперь прикрепите **фотографию** или примеры услуги.")
    return CREATE_LISTING_PHOTO

async def create_listing_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка фото объявления"""
    if not update.message.photo:
        await update.message.reply_text("Пожалуйста, отправьте именно фотографию.")
        return CREATE_LISTING_PHOTO
        
    photo_file = await update.message.photo[-1].get_file()
    
    # Сохранение фото локально
    photo_path = f"listing_photos/{update.effective_user.id}_{photo_file.file_unique_id}.jpg"
    os.makedirs("listing_photos", exist_ok=True)
    await photo_file.download_to_drive(photo_path)
    
    context.user_data['listing_photo_path'] = photo_path
    
    await update.message.reply_text("Введите **Стоимость** в звездах (⭐):")
    return CREATE_LISTING_PRICE

async def create_listing_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка цены объявления"""
    try:
        price = int(update.message.text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректную положительную стоимость в звездах.")
        return CREATE_LISTING_PRICE
        
    context.user_data['listing_price'] = price
    
    keyboard = [
        [InlineKeyboardButton("Товар", callback_data="listing_type_0")],
        [InlineKeyboardButton("Услуга", callback_data="listing_type_1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Это **Товар** или **Услуга**?", reply_markup=reply_markup)
    return ConversationHandler.END # Переход в CallbackQueryHandler

async def create_listing_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка типа объявления и сохранение"""
    query = update.callback_query
    await query.answer()
    
    is_service = int(query.data.split('_')[-1])
    
    success = DB.add_listing(
        query.from_user.id,
        context.user_data['listing_title'],
        "Описание будет добавлено позже", # Временно, для простоты
        context.user_data['listing_price'],
        is_service,
        context.user_data['listing_photo_path']
    )
    
    if success:
        await query.edit_message_text("✅ Объявление успешно создано и опубликовано на Рынке!")
    else:
        await query.edit_message_text("❌ Произошла ошибка при создании объявления.")
        
    context.user_data.clear()
    return ConversationHandler.END

async def my_listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображение объявлений предпринимателя"""
    user = update.effective_user
    if not DB.is_entrepreneur(user.id):
        await update.message.reply_text("У вас нет прав для управления объявлениями.")
        return
        
    listings = DB.get_user_listings(user.id)
    
    if not listings:
        await update.message.reply_text("У вас пока нет активных объявлений.")
        return
        
    message = "📦 **Ваши объявления:**\n\n"
    keyboard = []
    
    for listing in listings:
        listing_id, title, price, is_active = listing
        status = "✅ Активно" if is_active else "❌ Неактивно"
        
        message += f"**{title}** (ID: {listing_id}) - {price} ⭐ - {status}\n"
        
        keyboard.append([
            InlineKeyboardButton(f"Редактировать {listing_id}", callback_data=f"edit_listing_{listing_id}"),
            InlineKeyboardButton(f"Удалить {listing_id}", callback_data=f"delete_listing_{listing_id}")
        ])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

async def listing_management_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка колбэков управления объявлениями"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    action = data[0]
    listing_id = int(data[2])
    
    if action == 'delete':
        DB.delete_listing(listing_id)
        await query.edit_message_text(f"✅ Объявление ID {listing_id} успешно удалено.")
    elif action == 'edit':
        # Здесь должна быть логика редактирования, пока просто заглушка
        await query.edit_message_text(f"⚠️ Редактирование объявления ID {listing_id} пока не реализовано.")
        
    # Возвращаемся в меню объявлений
    await my_listings(query, context)

# ===== ФУНКЦИИ ПРЕДПРИНИМАТЕЛЯ: ПРОМОКОДЫ =====

async def create_promo_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало создания промокода"""
    user = update.effective_user
    if not DB.is_entrepreneur(user.id):
        await update.message.reply_text("У вас нет прав для создания промокодов.")
        return ConversationHandler.END
        
    await update.message.reply_text("Введите **уникальный код** для вашего промокода (например, `MYPROMO10`):")
    return CREATE_PROMO_CODE

async def create_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка кода промокода"""
    promo_code = update.message.text.strip().upper()
    
    if DB.get_promocode(promo_code): # Нужна функция get_promocode в database.py
        await update.message.reply_text("Промокод с таким кодом уже существует. Введите другой:")
        return CREATE_PROMO_CODE
        
    context.user_data['promo_code'] = promo_code
    await update.message.reply_text("Введите **размер скидки** в процентах (например, `10` для 10%):")
    return CREATE_PROMO_DISCOUNT

async def create_promo_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка скидки и сохранение промокода"""
    try:
        discount = int(update.message.text)
        if not 1 <= discount <= 100:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректный процент скидки (от 1 до 100).")
        return CREATE_PROMO_DISCOUNT
        
    success = DB.add_promocode(context.user_data['promo_code'], discount) # Нужна функция add_promocode в database.py
    
    if success:
        await update.message.reply_text(
            f"✅ Промокод **{context.user_data['promo_code']}** со скидкой **{discount}%** успешно создан.\n"
            f"Он будет действовать только на ваши товары и услуги."
        )
    else:
        await update.message.reply_text("❌ Произошла ошибка при создании промокода.")
        
    context.user_data.clear()
    return ConversationHandler.END

# ===== ФУНКЦИИ ПОКУПАТЕЛЯ: ПРОМОКОД =====

async def apply_promo_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало ввода промокода"""
    await update.message.reply_text("Введите промокод, который вы хотите применить:")
    return CREATE_PROMO_CODE # Используем то же состояние для ввода кода

async def apply_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка введенного промокода"""
    promo_code = update.message.text.strip().upper()
    promo = DB.get_promocode(promo_code) # Нужна функция get_promocode в database.py
    
    if promo:
        promo_id, user_id, code, discount, is_active, created_at = promo
        seller_user = DB.get_user(DB.get_user_by_id(user_id)[1]) # Нужна функция get_user_by_id
        
        await update.message.reply_text(
            f"✅ Промокод **{code}** найден!\n"
            f"**Скидка:** {discount}%\n"
            f"**Действует на товары:** @{seller_user[2]} ({seller_user[3]})\n\n"
            f"Скидка будет автоматически применена при покупке товаров этого предпринимателя."
        )
        # Здесь можно сохранить промокод в user_data для применения при покупке
        context.user_data['active_promo'] = promo
    else:
        await update.message.reply_text("❌ Промокод не найден или не активен. Попробуйте еще раз:")
        return CREATE_PROMO_CODE
        
    return ConversationHandler.END

# ===== ФУНКЦИИ ПОКУПАТЕЛЯ: ПОВЫШЕНИЕ =====

async def application_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало подачи заявки на Предпринимателя"""
    user = update.effective_user
    db_user = DB.get_user(user.id)
    
    if db_user[4] != 'Покупатель':
        await update.message.reply_text(f"Ваша текущая роль '{db_user[4]}'. Повышение не требуется.")
        return ConversationHandler.END
        
    await update.message.reply_text("Вы начали подачу заявки на роль **Предприниматель**.\nВведите ваше **Имя**:")
    return APPLICATION_NAME

async def application_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка имени"""
    context.user_data['app_name'] = update.message.text.strip()
    await update.message.reply_text("Введите **Название компании**:")
    return APPLICATION_COMPANY

async def application_company(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка названия компании"""
    context.user_data['app_company'] = update.message.text.strip()
    await update.message.reply_text("Перечислите **Услуги или товары**, которые вы будете предлагать:")
    return APPLICATION_PRODUCTS

async def application_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка товаров/услуг"""
    context.user_data['app_products'] = update.message.text.strip()
    await update.message.reply_text("Напишите **Немного о себе**:")
    return APPLICATION_ABOUT

async def application_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка информации о себе"""
    context.user_data['app_about'] = update.message.text.strip()
    await update.message.reply_text("Опишите ваш **Опыт работы** в этой сфере:")
    return APPLICATION_EXPERIENCE

async def application_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка опыта и создание заявки"""
    user = update.effective_user
    experience = update.message.text.strip()
    
    success, application_id = DB.create_entrepreneur_application(
        user.id,
        context.user_data['app_name'],
        context.user_data['app_company'],
        context.user_data['app_products'],
        context.user_data['app_about'],
        experience
    )
    
    if success:
        await update.message.reply_text("✅ Ваша заявка на повышение до Предпринимателя отправлена Владельцу на рассмотрение.")
        
        # Уведомление Владельца
        owner_user = DB.get_user(OWNER_TELEGRAM_ID)
        if owner_user:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"app_approve_{application_id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"app_reject_{application_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=OWNER_TELEGRAM_ID,
                text=(
                    f"🔔 **НОВАЯ ЗАЯВКА НА ПРЕДПРИНИМАТЕЛЯ**\n"
                    f"**ID Заявки:** {application_id}\n"
                    f"**Пользователь:** @{DB.get_user(user.id)[2]} ({user.first_name})\n"
                    f"**Компания:** {context.user_data['app_company']}\n"
                    f"**Товары/Услуги:** {context.user_data['app_products']}\n"
                    f"**Опыт:** {experience}"
                ),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text("❌ Произошла ошибка при отправке заявки.")
        
    context.user_data.clear()
    return ConversationHandler.END

# ===== ФУНКЦИИ ВЛАДЕЛЬЦА: УПРАВЛЕНИЕ РЕКВИЗИТАМИ =====

async def owner_requisites_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню управления реквизитами"""
    if not DB.is_owner(update.effective_user.id):
        await update.message.reply_text("У вас нет прав Владельца.")
        return
        
    requisites = DB.get_all_requisites()
    message = "**Управление реквизитами для пополнения:**\n\n"
    
    keyboard = []
    for req in requisites:
        req_id, name, details, is_active = req
        status = "✅ Активен" if is_active else "❌ Неактивен"
        action = "Деактивировать" if is_active else "Активировать"
        
        message += f"**ID {req_id}:** {name} ({status})\n"
        message += f"Детали: `{details}`\n"
        keyboard.append([InlineKeyboardButton(f"{action} {name}", callback_data=f"req_toggle_{req_id}_{0 if is_active else 1}")])
        
    keyboard.append([InlineKeyboardButton("➕ Добавить новый реквизит", callback_data="req_add")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

async def owner_requisites_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка колбэков управления реквизитами"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    action = data[1]
    
    if action == 'add':
        await query.edit_message_text("Введите **Название** реквизита (например, `Сбербанк`, `QR-код`):")
        return ADMIN_ADD_REQUISITE_NAME
    elif action == 'toggle':
        req_id = int(data[2])
        new_status = int(data[3])
        DB.toggle_requisite_status(req_id, new_status)
        await query.edit_message_text("✅ Статус реквизита обновлен. Возвращаюсь в меню.")
        await owner_requisites_menu(query, context)
        return ConversationHandler.END

async def admin_add_requisite_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка названия нового реквизита"""
    context.user_data['req_name'] = update.message.text.strip()
    await update.message.reply_text("Введите **Детали** реквизита (номер карты, номер телефона, описание QR-кода):")
    return ADMIN_ADD_REQUISITE_DETAILS

async def admin_add_requisite_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка деталей и сохранение реквизита"""
    details = update.message.text.strip()
    DB.add_requisite(context.user_data['req_name'], details)
    
    await update.message.reply_text("✅ Новый реквизит успешно добавлен.")
    context.user_data.clear()
    return ConversationHandler.END

# ===== ФУНКЦИИ ВЛАДЕЛЬЦА: РАССЫЛКА =====

async def owner_post_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало создания поста для рассылки"""
    if not DB.is_owner(update.effective_user.id):
        await update.message.reply_text("У вас нет прав Владельца.")
        return ConversationHandler.END
        
    await update.message.reply_text("Введите **текст поста** для рассылки. Вы можете использовать Markdown.")
    return ADMIN_POST_CONTENT

async def owner_post_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка контента поста и рассылка"""
    content = update.message.text
    owner_id = update.effective_user.id
    
    # Сохранение поста
    DB.add_post(content, owner_id)
    
    # Рассылка
    all_users = DB.get_all_users()
    
    for user_id in all_users:
        try:
            await context.bot.send_message(chat_id=user_id, text=content, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
            
    await update.message.reply_text(f"✅ Рассылка успешно завершена. Отправлено {len(all_users)} пользователям.")
    return ConversationHandler.END

# ===== ГЛАВНАЯ ФУНКЦИЯ =====

def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден в .env файле.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler для регистрации
    reg_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_username)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    application.add_handler(reg_handler)

    # ConversationHandler для пополнения
    replenish_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^⬆️ Пополнить баланс$"), replenish_start)],
        states={
            REPLENISH_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, replenish_amount)],
            REPLENISH_SCREENSHOT: [MessageHandler(filters.PHOTO & ~filters.COMMAND, replenish_screenshot)],
        },
        fallbacks=[MessageHandler(filters.Regex("^⬆️ Пополнить баланс$"), replenish_start)],
    )
    application.add_handler(replenish_handler)
    
    # CallbackQueryHandler для выбора реквизитов и запроса скриншота
    application.add_handler(CallbackQueryHandler(replenish_requisite_callback, pattern=r'^replenish_req_\d+$'))
    application.add_handler(CallbackQueryHandler(replenish_screenshot_prompt, pattern='^replenish_screenshot$'))
    
    # CallbackQueryHandler для админ-подтверждения пополнения
    application.add_handler(CallbackQueryHandler(admin_replenish_callback, pattern=r'^replenish_(confirm|reject)_\d+$'))

    # ConversationHandler для вывода
    withdraw_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^⬇️ Вывести баланс$"), withdraw_start)],
        states={
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
            WITHDRAW_REQUISITES: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_requisites)],
        },
        fallbacks=[MessageHandler(filters.Regex("^⬇️ Вывести баланс$"), withdraw_start)],
    )
    application.add_handler(withdraw_handler)
    
    # CallbackQueryHandler для вывода
    application.add_handler(CallbackQueryHandler(withdraw_amount_prompt, pattern='^withdraw_continue$'))
    application.add_handler(CallbackQueryHandler(withdraw_requisites_prompt, pattern='^withdraw_requisites$'))
    
    # CallbackQueryHandler для админ-подтверждения вывода
    application.add_handler(CallbackQueryHandler(owner_withdraw_callback, pattern=r'^withdraw_(confirm|reject)_\d+$'))

    # ConversationHandler для создания объявления
    listing_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Создать объявление$"), create_listing_start)],
        states={
            CREATE_LISTING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_listing_title)],
            CREATE_LISTING_PHOTO: [MessageHandler(filters.PHOTO & ~filters.COMMAND, create_listing_photo)],
            CREATE_LISTING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_listing_price)],
        },
        fallbacks=[MessageHandler(filters.Regex("^➕ Создать объявление$"), create_listing_start)],
    )
    application.add_handler(listing_handler)
    
    # CallbackQueryHandler для типа объявления
    application.add_handler(CallbackQueryHandler(create_listing_type_callback, pattern=r'^listing_type_\d+$'))
    
    # Обработчик для управления объявлениями
    application.add_handler(CallbackQueryHandler(listing_management_callback, pattern=r'^(edit|delete)_listing_\d+$'))
    
    # Обработчики для безопасной сделки
    application.add_handler(CallbackQueryHandler(buy_listing_callback, pattern=r'^buy_listing_\d+$'))
    application.add_handler(CallbackQueryHandler(complete_deal_callback, pattern=r'^complete_deal_\d+$'))
    application.add_handler(CallbackQueryHandler(arbitration_resolve_callback, pattern=r'^arb_resolve_\d+_\d+$'))
    
    # ConversationHandler для начала арбитража
    arbitration_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(arbitration_start_callback, pattern=r'^arbitration_start_\d+$')],
        states={
            ADMIN_COMPLAINT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, arbitration_reason)],
        },
        fallbacks=[CallbackQueryHandler(arbitration_start_callback, pattern=r'^arbitration_start_\d+$')],
    )
    application.add_handler(arbitration_handler)

    # ConversationHandler для создания промокода
    promo_create_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🏷️ Создать промокод$"), create_promo_start)],
        states={
            CREATE_PROMO_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_promo_code)],
            CREATE_PROMO_DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_promo_discount)],
        },
        fallbacks=[MessageHandler(filters.Regex("^🏷️ Создать промокод$"), create_promo_start)],
    )
    application.add_handler(promo_create_handler)

    # ConversationHandler для применения промокода
    promo_apply_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🏷️ Промокод$"), apply_promo_start)],
        states={
            CREATE_PROMO_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_promo_code)],
        },
        fallbacks=[MessageHandler(filters.Regex("^🏷️ Промокод$"), apply_promo_start)],
    )
    application.add_handler(promo_apply_handler)

    # ConversationHandler для заявки на Предпринимателя
    application_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🚀 Получить повышение$"), application_start)],
        states={
            APPLICATION_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, application_name)],
            APPLICATION_COMPANY: [MessageHandler(filters.TEXT & ~filters.COMMAND, application_company)],
            APPLICATION_PRODUCTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, application_products)],
            APPLICATION_ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, application_about)],
            APPLICATION_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, application_experience)],
        },
        fallbacks=[MessageHandler(filters.Regex("^🚀 Получить повышение$"), application_start)],
    )
    application.add_handler(application_handler)

    # CallbackQueryHandler для одобрения/отклонения заявки на Предпринимателя
    # application.add_handler(CallbackQueryHandler(owner_application_callback, pattern=r'^app_(approve|reject)_\d+$')) # Нужна реализация

    # ConversationHandler для добавления реквизитов (Владелец)
    req_add_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(owner_requisites_callback, pattern='^req_add$')],
        states={
            ADMIN_ADD_REQUISITE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_requisite_name)],
            ADMIN_ADD_REQUISITE_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_requisite_details)],
        },
        fallbacks=[CallbackQueryHandler(owner_requisites_callback, pattern='^req_add$')],
    )
    application.add_handler(req_add_handler)

    # ConversationHandler для рассылки (Владелец)
    post_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Рассылка$"), owner_post_start)],
        states={
            ADMIN_POST_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, owner_post_content)],
        },
        fallbacks=[MessageHandler(filters.Regex("^Рассылка$"), owner_post_start)],
    )
    application.add_handler(post_handler)

    # Основные обработчики
    application.add_handler(MessageHandler(filters.Regex("^👤 Профиль$"), profile))
    application.add_handler(MessageHandler(filters.Regex("^💰 Рынок$"), market))
    application.add_handler(MessageHandler(filters.Regex("^📦 Объявления$"), my_listings))
    application.add_handler(MessageHandler(filters.Regex("^Управление реквизитами$"), owner_requisites_menu))
    
    # Добавляем кнопки для админ-панели
    application.add_handler(MessageHandler(filters.Regex("^👥 Пользователи$"), admin_users_menu))
    application.add_handler(MessageHandler(filters.Regex("^⭐ Токены$"), owner_tokens_menu))
    application.add_handler(MessageHandler(filters.Regex("^⚠️ Жалобы$"), admin_complaints_menu))
    application.add_handler(MessageHandler(filters.Regex("^⚙️ Настройки$"), owner_settings_menu))
    
    # Добавляем кнопку "Пожаловаться" в основную клавиатуру для Покупателя
    application.add_handler(MessageHandler(filters.Regex("^⚠️ Пожаловаться$"), complaint_start))

    # Запуск бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Инициализация базы данных
    DB.init_db()
    
    # Создание папок для хранения файлов
    os.makedirs("replenishment_screenshots", exist_ok=True)
    os.makedirs("listing_photos", exist_ok=True)
    
    main()

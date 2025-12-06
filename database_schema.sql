-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL, -- Никнейм, который придумывает пользователь
    first_name TEXT,
    role TEXT DEFAULT 'Покупатель', -- Покупатель, Предприниматель, Администратор, Владелец
    balance INTEGER DEFAULT 0, -- Баланс в "Звездочках"
    frozen_balance INTEGER DEFAULT 0, -- Замороженный баланс во время сделки
    rating INTEGER DEFAULT 100, -- Рейтинг пользователя
    status TEXT DEFAULT 'Отличный', -- Отличный, На грани блокировки
    complaints_count INTEGER DEFAULT 0, -- Количество жалоб
    is_blocked BOOLEAN DEFAULT 0, -- Полная блокировка (Владелец)
    is_frozen BOOLEAN DEFAULT 0, -- Заморозка аккаунта (Администратор/Владелец)
    is_admin BOOLEAN DEFAULT 0, -- Флаг для быстрого доступа к админ-функциям
    is_owner BOOLEAN DEFAULT 0, -- Флаг для быстрого доступа к функциям владельца
    company_name TEXT, -- Название компании (для Предпринимателя)
    experience TEXT, -- Опыт работы (для Предпринимателя)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица объявлений (товары/услуги)
CREATE TABLE IF NOT EXISTS listings (
    listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, -- ID предпринимателя
    title TEXT NOT NULL,
    description TEXT,
    price INTEGER NOT NULL, -- Цена в "Звездочках"
    is_service BOOLEAN DEFAULT 0, -- 1 - Услуга, 0 - Товар
    photo_path TEXT, -- Путь к фото
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица заявок на пополнение
CREATE TABLE IF NOT EXISTS replenishment_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    rub_amount INTEGER NOT NULL,
    stars_amount INTEGER NOT NULL,
    screenshot_path TEXT,
    status TEXT DEFAULT 'pending', -- pending, confirmed, rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_by INTEGER, -- ID Владельца/Администратора, который обработал
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (processed_by) REFERENCES users(user_id)
);

-- Таблица заявок на вывод
CREATE TABLE IF NOT EXISTS withdrawal_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    stars_amount INTEGER NOT NULL, -- Запрашиваемая сумма в Звездах
    rub_amount INTEGER NOT NULL, -- Сумма к выплате в Рублях (с учетом 15% комиссии)
    requisites TEXT NOT NULL, -- Реквизиты для выплаты
    status TEXT DEFAULT 'pending', -- pending, confirmed, rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_by INTEGER, -- ID Владельца, который обработал
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (processed_by) REFERENCES users(user_id)
);

-- Таблица реквизитов для пополнения (добавляет Владелец)
CREATE TABLE IF NOT EXISTS owner_requisites (
    requisite_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, -- Название (например, "Сбербанк", "QR-код")
    details TEXT NOT NULL, -- Реквизиты или описание QR-кода
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица промокодов (создает Предприниматель)
CREATE TABLE IF NOT EXISTS promocodes (
    promo_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, -- ID предпринимателя, создавшего промокод
    code TEXT UNIQUE NOT NULL,
    discount_percent INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица сделок (для механизма "Безопасной сделки")
CREATE TABLE IF NOT EXISTS deals (
    deal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER,
    seller_id INTEGER,
    listing_id INTEGER,
    price INTEGER NOT NULL, -- Цена сделки
    status TEXT DEFAULT 'pending', -- pending, accepted, successful, canceled_by_user, arbitration, canceled_by_admin
    is_frozen BOOLEAN DEFAULT 1, -- Флаг заморозки средств
    arbitrator_id INTEGER, -- ID Администратора, который занимается арбитражем
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (buyer_id) REFERENCES users(user_id),
    FOREIGN KEY (seller_id) REFERENCES users(user_id),
    FOREIGN KEY (listing_id) REFERENCES listings(listing_id),
    FOREIGN KEY (arbitrator_id) REFERENCES users(user_id)
);

-- Таблица отзывов
CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id INTEGER,
    reviewer_id INTEGER, -- ID покупателя
    seller_id INTEGER, -- ID предпринимателя
    rating INTEGER, -- Оценка (например, 1-5)
    text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deal_id) REFERENCES deals(deal_id),
    FOREIGN KEY (reviewer_id) REFERENCES users(user_id),
    FOREIGN KEY (seller_id) REFERENCES users(user_id)
);

-- Таблица жалоб
CREATE TABLE IF NOT EXISTS complaints (
    complaint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id INTEGER, -- ID подавшего жалобу
    target_id INTEGER, -- ID, на кого подана жалоба
    deal_id INTEGER, -- ID сделки, если жалоба связана со сделкой
    reason TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, resolved, rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_by INTEGER, -- ID Администратора/Владельца, который обработал
    FOREIGN KEY (reporter_id) REFERENCES users(user_id),
    FOREIGN KEY (target_id) REFERENCES users(user_id),
    FOREIGN KEY (deal_id) REFERENCES deals(deal_id),
    FOREIGN KEY (resolved_by) REFERENCES users(user_id)
);

-- Таблица заявок на повышение до Предпринимателя
CREATE TABLE IF NOT EXISTS entrepreneur_applications (
    application_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    company_name TEXT,
    products_services TEXT,
    about_me TEXT,
    experience TEXT,
    status TEXT DEFAULT 'pending', -- pending, approved, rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_by INTEGER, -- ID Владельца, который обработал
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (processed_by) REFERENCES users(user_id)
);

-- Таблица конкурсов (для Предпринимателя)
CREATE TABLE IF NOT EXISTS contests (
    contest_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, -- ID предпринимателя
    title TEXT NOT NULL,
    description TEXT,
    prize INTEGER NOT NULL, -- Приз в "Звездочках"
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица постов (рассылок)
CREATE TABLE IF NOT EXISTS posts (
    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

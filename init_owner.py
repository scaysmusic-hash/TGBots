import os
from database import Database
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
OWNER_TELEGRAM_ID = int(os.getenv("OWNER_TELEGRAM_ID", 0))

if OWNER_TELEGRAM_ID == 0:
    print("Ошибка: OWNER_TELEGRAM_ID не установлен в .env файле.")
    exit()

DB = Database()

def init_owner():
    """Инициализация владельца бота"""
    # Предполагаем, что владелец уже зарегистрировался через /start
    owner_user = DB.get_user(OWNER_TELEGRAM_ID)
    
    if not owner_user:
        print(f"Ошибка: Пользователь с Telegram ID {OWNER_TELEGRAM_ID} не найден в базе данных.")
        print("Пожалуйста, сначала запустите бота и отправьте ему команду /start с аккаунта владельца.")
        return

    # Проверяем и устанавливаем роль "Владелец"
    if owner_user[4] != 'Владелец':
        DB.update_role(OWNER_TELEGRAM_ID, 'Владелец')
        print(f"✅ Роль пользователя {owner_user[2]} (ID: {OWNER_TELEGRAM_ID}) успешно установлена на 'Владелец'.")
    else:
        print(f"ℹ️ Пользователь {owner_user[2]} уже является 'Владельцем'.")

if __name__ == "__main__":
    init_owner()

# Примеры использования API (Внутренние функции)

Данный файл содержит примеры вызова ключевых функций из модуля `database.py` для тестирования и отладки.

## Инициализация

```python
from database import Database

# Инициализация базы данных
DB = Database()
```

## 1. Управление пользователями и ролями

### Регистрация нового пользователя
```python
# Предполагаем, что 123456789 - это Telegram ID
DB.add_user(telegram_id=123456789, first_name="TestUser", username="test_user")
```

### Смена роли
```python
# Смена роли пользователя 123456789 на 'Предприниматель'
DB.change_role(telegram_id=123456789, new_role='Предприниматель')
```

### Блокировка/Разблокировка
```python
# Блокировка пользователя
DB.block_user(telegram_id=123456789, is_blocked=1)

# Разблокировка пользователя
DB.block_user(telegram_id=123456789, is_blocked=0)
```

## 2. Финансовые операции

### Начисление/Списание баланса
```python
# Начисление 100 Звездочек
DB.update_balance(telegram_id=123456789, amount=100)

# Списание 50 Звездочек
DB.update_balance(telegram_id=123456789, amount=-50)
```

### Создание запроса на пополнение
```python
# Запрос на пополнение на 500 рублей (500 Звездочек)
DB.add_deposit_request(telegram_id=123456789, amount=500, photo_path="/path/to/screenshot.jpg")
```

### Подтверждение запроса на пополнение (Администратор)
```python
# Подтверждение запроса ID 1
DB.resolve_deposit_request(request_id=1, admin_telegram_id=987654321, is_approved=True)
```

## 3. Управление объявлениями

### Создание объявления (Предприниматель)
```python
# Получаем внутренний user_id предпринимателя
user_id = DB.get_user(telegram_id=123456789)[0]

DB.add_listing(
    user_id=user_id,
    title="Тестовый товар",
    description="Отличное описание товара",
    price=50,
    is_service=0, # 0 - Товар, 1 - Услуга
    photo_path="/path/to/photo.jpg"
)
```

### Удаление объявления
```python
DB.delete_listing(listing_id=1)
```

## 4. Безопасная сделка

### Создание сделки (Покупатель)
```python
# Покупатель 123456789 покупает объявление ID 2 за 50 Звездочек
success, result = DB.create_safe_deal(buyer_telegram_id=123456789, listing_id=2, amount=50)
if success:
    deal_id = result
    print(f"Сделка создана, ID: {deal_id}")
else:
    print(f"Ошибка: {result}")
```

### Завершение сделки (Покупатель/Продавец)
```python
# Завершение сделки ID 1
DB.complete_safe_deal(deal_id=1, completer_telegram_id=123456789)
```

### Начало арбитража
```python
# Начало арбитража по сделке ID 1
DB.start_arbitration(deal_id=1, complainer_telegram_id=123456789, reason="Товар не доставлен")
```

### Разрешение арбитража (Администратор)
```python
# Администратор 987654321 решает, что победил Покупатель 123456789
DB.resolve_arbitration(deal_id=1, winner_telegram_id=123456789, admin_telegram_id=987654321)
```

## 5. Система репутации

### Добавление жалобы
```python
# Пользователь 123456789 жалуется на 111111111
DB.add_complaint(complainer_telegram_id=123456789, target_telegram_id=111111111, reason="Мошенничество")
```

### Разрешение жалобы (Администратор)
```python
# Администратор 987654321 разрешает жалобу ID 1
# Снижает рейтинг на 10 и устанавливает статус 'Критический'
DB.resolve_complaint(
    complaint_id=1, 
    admin_telegram_id=987654321, 
    new_rating=-10, 
    new_status='Критический'
)
```

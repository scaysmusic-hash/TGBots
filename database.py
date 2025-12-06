import sqlite3
import os
import random
import string
from datetime import datetime

class Database:
    def __init__(self, db_name="market_database.db"):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Чтение и выполнение SQL-схемы
        schema_path = os.path.join(os.path.dirname(__file__), "database_schema.sql")
        with open(schema_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        cursor.executescript(sql_script)
        conn.commit()
        conn.close()

    def generate_unique_username(self):
        """Генерация уникального никнейма"""
        while True:
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if not cursor.fetchone():
                conn.close()
                return username
            conn.close()

    # ===== ПОЛЬЗОВАТЕЛИ И РОЛИ =====

    def add_user(self, telegram_id, first_name, username):
        """Добавление нового пользователя (Покупатель)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (telegram_id, first_name, username)
                VALUES (?, ?, ?)
            ''', (telegram_id, first_name, username))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_user(self, telegram_id):
        """Получение информации о пользователе"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    def get_user_by_username(self, username):
        """Получение информации о пользователе по никнейму"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        return user

    def get_user_by_id(self, user_id):
        """Получение информации о пользователе по внутреннему user_id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    def update_rating(self, telegram_id, rating_change):
        """Обновление рейтинга пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET rating = rating + ? WHERE telegram_id = ?", 
                       (rating_change, telegram_id))
        conn.commit()
        conn.close()

    def update_status(self, telegram_id, new_status):
        """Обновление статуса аккаунта пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = ? WHERE telegram_id = ?", 
                       (new_status, telegram_id))
        conn.commit()
        conn.close()

    def add_complaint(self, complainer_telegram_id, target_telegram_id, reason):
        """Добавление жалобы"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (complainer_telegram_id,))
            complainer_id = cursor.fetchone()[0]
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (target_telegram_id,))
            target_id = cursor.fetchone()[0]
            
            cursor.execute('''
                INSERT INTO complaints (complainer_id, target_id, reason)
                VALUES (?, ?, ?)
            ''', (complainer_id, target_id, reason))
            complaint_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return True, complaint_id
        except Exception as e:
            conn.close()
            return False, str(e)

    def get_pending_complaints(self):
        """Получение ожидающих рассмотрения жалоб"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                c.complaint_id, u1.username AS complainer_username, u2.username AS target_username, c.reason, c.created_at
            FROM complaints c
            JOIN users u1 ON c.complainer_id = u1.user_id
            JOIN users u2 ON c.target_id = u2.user_id
            WHERE c.status = 'pending'
            ORDER BY c.created_at ASC
        ''')
        complaints = cursor.fetchall()
        conn.close()
        return complaints

    def resolve_complaint(self, complaint_id, admin_telegram_id, new_rating, new_status):
        """Разрешение жалобы администратором"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 1. Обновляем статус жалобы
            cursor.execute("UPDATE complaints SET status = 'resolved', resolved_by = ? WHERE complaint_id = ?", 
                           (admin_telegram_id, complaint_id))
                           
            # 2. Получаем ID цели
            cursor.execute("SELECT target_id FROM complaints WHERE complaint_id = ?", (complaint_id,))
            target_user_id = cursor.fetchone()[0]
            target_telegram_id = self.get_user_by_id(target_user_id)[1]
            
            # 3. Обновляем рейтинг и статус цели
            self.update_rating(target_telegram_id, new_rating)
            self.update_status(target_telegram_id, new_status)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.close()
            return False

    def update_balance(self, telegram_id, amount):
        """Обновление баланса пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET balance = balance + ? WHERE telegram_id = ?
        ''', (amount, telegram_id))
        conn.commit()
        conn.close()

    def update_role(self, telegram_id, new_role):
        """Обновление роли пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        is_admin = 1 if new_role == 'Администратор' else 0
        is_owner = 1 if new_role == 'Владелец' else 0
        cursor.execute('''
            UPDATE users SET role = ?, is_admin = ?, is_owner = ? WHERE telegram_id = ?
        ''', (new_role, is_admin, is_owner, telegram_id))
        conn.commit()
        conn.close()

    def get_all_users(self):
        """Получение всех пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id FROM users")
        users = cursor.fetchall()
        conn.close()
        return [user[0] for user in users]

    # ===== АДМИНИСТРАТИВНЫЕ ФУНКЦИИ =====

    def is_owner(self, telegram_id):
        """Проверка, является ли пользователь Владельцем"""
        user = self.get_user(telegram_id)
        return user and user[13] == 1 # is_owner

    def is_admin_or_owner(self, telegram_id):
        """Проверка, является ли пользователь Администратором или Владельцем"""
        user = self.get_user(telegram_id)
        return user and (user[12] == 1 or user[13] == 1) # is_admin or is_owner

    def is_entrepreneur(self, telegram_id):
        """Проверка, является ли пользователь Предпринимателем или выше"""
        user = self.get_user(telegram_id)
        return user and user[4] in ('Предприниматель', 'Администратор', 'Владелец')

    def is_blocked(self, telegram_id):
        """Проверка, заблокирован ли пользователь"""
        user = self.get_user(telegram_id)
        return user and user[10] == 1 # is_blocked

    def is_frozen(self, telegram_id):
        """Проверка, заморожен ли аккаунт"""
        user = self.get_user(telegram_id)
        return user and user[11] == 1 # is_frozen

    def block_user(self, telegram_id):
        """Блокировка пользователя (Владелец)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_blocked = 1 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        conn.close()

    def unblock_user(self, telegram_id):
        """Разблокировка пользователя (Владелец)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_blocked = 0 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        conn.close()

    def freeze_user(self, telegram_id):
        """Заморозка аккаунта (Администратор/Владелец)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_frozen = 1 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        conn.close()

    def unfreeze_user(self, telegram_id):
        """Разморозка аккаунта (Администратор/Владелец)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_frozen = 0 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        conn.close()

    # ===== РЕКВИЗИТЫ ВЛАДЕЛЬЦА =====

    def add_requisite(self, name, details):
        """Добавление реквизита для пополнения"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO owner_requisites (name, details)
            VALUES (?, ?)
        ''', (name, details))
        conn.commit()
        conn.close()

    def get_active_requisites(self):
        """Получение всех активных реквизитов"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT requisite_id, name, details FROM owner_requisites WHERE is_active = 1")
        requisites = cursor.fetchall()
        conn.close()
        return requisites

    def toggle_requisite_status(self, requisite_id, is_active):
        """Переключение статуса реквизита"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE owner_requisites SET is_active = ? WHERE requisite_id = ?", (is_active, requisite_id))
        conn.commit()
        conn.close()

    def get_all_requisites(self):
        """Получение всех реквизитов (для админ-панели)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT requisite_id, name, is_active FROM owner_requisites")
        requisites = cursor.fetchall()
        conn.close()
        return requisites

    # ===== ПОПОЛНЕНИЕ И ВЫВОД =====

    def create_replenishment_request(self, user_id, rub_amount, stars_amount, screenshot_path):
        """Создание заявки на пополнение"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO replenishment_requests (user_id, rub_amount, stars_amount, screenshot_path)
            VALUES (?, ?, ?, ?)
        ''', (user_id, rub_amount, stars_amount, screenshot_path))
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return request_id

    def get_pending_replenishments(self):
        """Получение ожидающих подтверждения заявок на пополнение"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                r.request_id, u.telegram_id, u.first_name, r.rub_amount, r.stars_amount, r.screenshot_path, r.created_at
            FROM replenishment_requests r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.status = 'pending'
            ORDER BY r.created_at ASC
        ''')
        requests = cursor.fetchall()
        conn.close()
        return requests

    def confirm_replenishment(self, request_id, admin_telegram_id):
        """Подтверждение заявки на пополнение"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Получаем данные заявки
            cursor.execute("SELECT user_id, stars_amount FROM replenishment_requests WHERE request_id = ? AND status = 'pending'", (request_id,))
            request = cursor.fetchone()
            
            if not request:
                return False, "Заявка не найдена или уже обработана"
            
            user_id, stars_amount = request
            
            # 2. Получаем telegram_id пользователя
            cursor.execute("SELECT telegram_id FROM users WHERE user_id = ?", (user_id,))
            user_telegram_id = cursor.fetchone()[0]
            
            # 3. Начисляем звезды
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (stars_amount, user_id))
            
            # 4. Обновляем статус заявки
            cursor.execute('''
                UPDATE replenishment_requests SET status = 'confirmed', processed_by = (SELECT user_id FROM users WHERE telegram_id = ?), confirmed_at = ?
                WHERE request_id = ?
            ''', (admin_telegram_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), request_id))
            
            conn.commit()
            return True, user_telegram_id, stars_amount
        except Exception as e:
            conn.rollback()
            print(f"Error confirming replenishment: {e}")
            return False, "Ошибка базы данных"
        finally:
            conn.close()

    def reject_replenishment(self, request_id, admin_telegram_id):
        """Отклонение заявки на пополнение"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Получаем данные заявки
            cursor.execute("SELECT user_id FROM replenishment_requests WHERE request_id = ? AND status = 'pending'", (request_id,))
            request = cursor.fetchone()
            
            if not request:
                return False, "Заявка не найдена или уже обработана"
            
            user_id = request[0]
            
            # 2. Получаем telegram_id пользователя
            cursor.execute("SELECT telegram_id FROM users WHERE user_id = ?", (user_id,))
            user_telegram_id = cursor.fetchone()[0]
            
            # 3. Обновляем статус заявки
            cursor.execute('''
                UPDATE replenishment_requests SET status = 'rejected', processed_by = (SELECT user_id FROM users WHERE telegram_id = ?), confirmed_at = ?
                WHERE request_id = ?
            ''', (admin_telegram_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), request_id))
            
            conn.commit()
            return True, user_telegram_id
        except Exception as e:
            conn.rollback()
            print(f"Error rejecting replenishment: {e}")
            return False, "Ошибка базы данных"
        finally:
            conn.close()

    def create_withdrawal_request(self, user_id, stars_amount, rub_amount, requisites):
        """Создание заявки на вывод"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO withdrawal_requests (user_id, stars_amount, rub_amount, requisites)
            VALUES (?, ?, ?, ?)
        ''', (user_id, stars_amount, rub_amount, requisites))
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return request_id

    def get_pending_withdrawals(self):
        """Получение ожидающих подтверждения заявок на вывод"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                w.request_id, u.telegram_id, u.first_name, w.stars_amount, w.rub_amount, w.requisites, w.created_at
            FROM withdrawal_requests w
            JOIN users u ON w.user_id = u.user_id
            WHERE w.status = 'pending'
            ORDER BY w.created_at ASC
        ''')
        requests = cursor.fetchall()
        conn.close()
        return requests

    def get_withdrawal_request(self, request_id):
        """Получение заявки на вывод по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM withdrawal_requests WHERE request_id = ?", (request_id,))
        request = cursor.fetchone()
        conn.close()
        return request

    def confirm_withdrawal(self, request_id, owner_telegram_id):
        """Подтверждение заявки на вывод (Владелец)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Получаем данные заявки
            cursor.execute("SELECT user_id, stars_amount FROM withdrawal_requests WHERE request_id = ? AND status = 'pending'", (request_id,))
            request = cursor.fetchone()
            
            if not request:
                return False, "Заявка не найдена или уже обработана"
            
            user_id, stars_amount = request
            
            # 2. Получаем telegram_id пользователя
            cursor.execute("SELECT telegram_id FROM users WHERE user_id = ?", (user_id,))
            user_telegram_id = cursor.fetchone()[0]
            
            # 3. Списываем звезды
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (stars_amount, user_id))
            
            # 4. Обновляем статус заявки
            cursor.execute('''
                UPDATE withdrawal_requests SET status = 'confirmed', processed_by = (SELECT user_id FROM users WHERE telegram_id = ?), confirmed_at = ?
                WHERE request_id = ?
            ''', (owner_telegram_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), request_id))
            
            conn.commit()
            return True, user_telegram_id
        except Exception as e:
            conn.rollback()
            print(f"Error confirming withdrawal: {e}")
            return False, "Ошибка базы данных"
        finally:
            conn.close()

    def reject_withdrawal(self, request_id, owner_telegram_id):
        """Отклонение заявки на вывод (Владелец)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Получаем данные заявки
            cursor.execute("SELECT user_id FROM withdrawal_requests WHERE request_id = ? AND status = 'pending'", (request_id,))
            request = cursor.fetchone()
            
            if not request:
                return False, "Заявка не найдена или уже обработана"
            
            user_id = request[0]
            
            # 2. Получаем telegram_id пользователя
            cursor.execute("SELECT telegram_id FROM users WHERE user_id = ?", (user_id,))
            user_telegram_id = cursor.fetchone()[0]
            
            # 3. Обновляем статус заявки
            cursor.execute('''
                UPDATE withdrawal_requests SET status = 'rejected', processed_by = (SELECT user_id FROM users WHERE telegram_id = ?), confirmed_at = ?
                WHERE request_id = ?
            ''', (owner_telegram_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), request_id))
            
            conn.commit()
            return True, user_telegram_id
        except Exception as e:
            conn.rollback()
            print(f"Error rejecting withdrawal: {e}")
            return False, "Ошибка базы данных"
        finally:
            conn.close()

    # ===== ОБЪЯВЛЕНИЯ (LISTINGS) =====

    def add_listing(self, telegram_id, title, description, price, is_service, photo_path):
        """Добавление нового объявления"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (telegram_id,))
            user_id = cursor.fetchone()[0]
            
            cursor.execute('''
                INSERT INTO listings (user_id, title, description, price, is_service, photo_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, title, description, price, is_service, photo_path))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding listing: {e}")
            return False
        finally:
            conn.clos    def get_all_active_listings(self):
        """Получение всех активных объявлений для рынка"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                l.listing_id, l.title, l.description, l.price, l.is_service, l.photo_path,
                u.first_name, u.username, u.rating
            FROM listings l
            JOIN users u ON l.user_id = u.user_id
            WHERE l.is_active = 1
            ORDER BY l.created_at DESC
        ''')
        listings = cursor.fetchall()
        conn.close()
        return listings

    def get_listing_by_id(self, listing_id):
        """Получение объявления по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                l.listing_id, l.title, l.description, l.price, l.is_service, l.photo_path,
                u.telegram_id, u.username, u.rating
            FROM listings l
            JOIN users u ON l.user_id = u.user_id
            WHERE l.listing_id = ?
        ''', (listing_id,))
        listing = cursor.fetchone()
        conn.close()
        return listing

    def create_safe_deal(self, buyer_telegram_id, listing_id, amount):
        """Создание безопасной сделки (заморозка средств)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 1. Получаем ID покупателя и продавца
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (buyer_telegram_id,))
            buyer_user_id = cursor.fetchone()[0]
            
            listing = self.get_listing_by_id(listing_id)
            if not listing:
                return False, "Объявление не найдено"
            seller_telegram_id = listing[6]
            
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (seller_telegram_id,))
            seller_user_id = cursor.fetchone()[0]
            
            # 2. Проверяем баланс
            cursor.execute("SELECT balance FROM users WHERE telegram_id = ?", (buyer_telegram_id,))
            buyer_balance = cursor.fetchone()[0]
            if buyer_balance < amount:
                return False, "Недостаточно средств"
                
            # 3. Списываем с баланса и зачисляем в замороженный баланс
            cursor.execute("UPDATE users SET balance = balance - ?, frozen_balance = frozen_balance + ? WHERE telegram_id = ?", 
                           (amount, amount, buyer_telegram_id))
                           
            # 4. Создаем запись о сделке
            cursor.execute('''
                INSERT INTO safe_deals (buyer_id, seller_id, listing_id, amount, status)
                VALUES (?, ?, ?, ?, 'pending')
            ''', (buyer_user_id, seller_user_id, listing_id, amount))
            deal_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            return True, deal_id
        except Exception as e:
            conn.close()
            return False, str(e)

    def get_safe_deal(self, deal_id):
        """Получение информации о безопасной сделке"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM safe_deals WHERE deal_id = ?", (deal_id,))
        deal = cursor.fetchone()
        conn.close()
        return deal

    def complete_safe_deal(self, deal_id, completer_telegram_id):
        """Завершение безопасной сделки (перевод средств продавцу)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            deal = self.get_safe_deal(deal_id)
            if not deal or deal[5] != 'pending':
                return False, "Сделка не найдена или уже завершена/отменена"
                
            # Проверяем, что завершает либо покупатель, либо продавец
            buyer_telegram_id = self.get_user_by_id(deal[1])[1]
            seller_telegram_id = self.get_user_by_id(deal[2])[1]
            
            if completer_telegram_id not in (buyer_telegram_id, seller_telegram_id):
                return False, "Только участники сделки могут ее завершить"
                
            # 1. Списываем с замороженного баланса покупателя
            cursor.execute("UPDATE users SET frozen_balance = frozen_balance - ? WHERE telegram_id = ?", 
                           (deal[4], buyer_telegram_id))
                           
            # 2. Зачисляем на баланс продавца
            cursor.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", 
                           (deal[4], seller_telegram_id))
                           
            # 3. Обновляем статус сделки
            cursor.execute("UPDATE safe_deals SET status = 'completed', completed_by = ? WHERE deal_id = ?", 
                           (completer_telegram_id, deal_id))
                           
            conn.commit()
            conn.close()
            return True, "Сделка успешно завершена"
        except Exception as e:
            conn.close()
            return False, str(e)

    def start_arbitration(self, deal_id, complainer_telegram_id, reason):
        """Начало арбитража"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            deal = self.get_safe_deal(deal_id)
            if not deal or deal[5] != 'pending':
                return False, "Сделка не найдена или уже завершена/отменена"
                
            # Проверяем, что арбитраж начинает участник сделки
            buyer_telegram_id = self.get_user_by_id(deal[1])[1]
            seller_telegram_id = self.get_user_by_id(deal[2])[1]
            
            if complainer_telegram_id not in (buyer_telegram_id, seller_telegram_id):
                return False, "Только участники сделки могут начать арбитраж"
                
            # Обновляем статус сделки
            cursor.execute("UPDATE safe_deals SET status = 'arbitration', arbitration_reason = ? WHERE deal_id = ?", 
                           (reason, deal_id))
                           
            conn.commit()
            conn.close()
            return True, "Арбитраж начат"
        except Exception as e:
            conn.close()
            return False, str(e)

    def resolve_arbitration(self, deal_id, winner_telegram_id, admin_telegram_id):
        """Разрешение арбитража администратором"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            deal = self.get_safe_deal(deal_id)
            if not deal or deal[5] != 'arbitration':
                return False, "Сделка не найдена или не находится в статусе арбитража"
                
            # Проверяем, что разрешает администратор
            if not self.is_admin(admin_telegram_id):
                return False, "Только администратор может разрешать арбитраж"
                
            buyer_telegram_id = self.get_user_by_id(deal[1])[1]
            seller_telegram_id = self.get_user_by_id(deal[2])[1]
            
            # 1. Списываем с замороженного баланса покупателя
            cursor.execute("UPDATE users SET frozen_balance = frozen_balance - ? WHERE telegram_id = ?", 
                           (deal[4], buyer_telegram_id))
                           
            # 2. Зачисляем на баланс победителя
            if winner_telegram_id == buyer_telegram_id:
                # Возврат покупателю
                cursor.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", 
                               (deal[4], buyer_telegram_id))
                status = 'arbitration_refunded'
            elif winner_telegram_id == seller_telegram_id:
                # Перевод продавцу
                cursor.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", 
                               (deal[4], seller_telegram_id))
                status = 'arbitration_completed'
            else:
                return False, "Неверный победитель"
                
            # 3. Обновляем статус сделки
            cursor.execute("UPDATE safe_deals SET status = ?, resolved_by = ? WHERE deal_id = ?", 
                           (status, admin_telegram_id, deal_id))
                           
            conn.commit()
            conn.close()
            return True, "Арбитраж разрешен"
        except Exception as e:
            conn.close()
            return False, str(e)et_listing(self, listing_id):
        """Получение объявления по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                l.listing_id, l.user_id, l.title, l.description, l.price, l.is_service, l.photo_path, u.telegram_id
            FROM listings l
            JOIN users u ON l.user_id = u.user_id
            WHERE l.listing_id = ?
        ''', (listing_id,))
        listing = cursor.fetchone()
        conn.close()
        return listing

    def get_user_listings(self, telegram_id):
        """Получение объявлений предпринимателя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                l.listing_id, l.title, l.price, l.is_active
            FROM listings l
            JOIN users u ON l.user_id = u.user_id
            WHERE u.telegram_id = ?
            ORDER BY l.created_at DESC
        ''', (telegram_id,))
        listings = cursor.fetchall()
        conn.close()
        return listings

    def delete_listing(self, listing_id):
        """Удаление объявления"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM listings WHERE listing_id = ?", (listing_id,))
        conn.commit()
        conn.close()

    # ===== ПРОМОКОДЫ =====

    def add_promocode(self, user_telegram_id, code, discount_percent):
        """Добавление промокода"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (user_telegram_id,))
            user_id = cursor.fetchone()[0]
            
            cursor.execute('''
                INSERT INTO promocodes (user_id, code, discount_percent)
                VALUES (?, ?, ?)
            ''', (user_id, code, discount_percent))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False

    def get_promocode(self, code):
        """Получение промокода"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM promocodes WHERE code = ? AND is_active = 1", (code,))
        promo = cursor.fetchone()
        conn.close()
        return promo

    def delete_listing(self, listing_id):
        """Удаление объявления (Предприниматель)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE listings SET is_active = 0 WHERE listing_id = ?", (listing_id,))
        conn.commit()
        conn.close()

    def admin_delete_listing(self, listing_id):
        """Удаление объявления (Администратор/Владелец)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE listings SET is_active = 0 WHERE listing_id = ?", (listing_id,))
        conn.commit()
        conn.close()

    def admin_change_listing_price(self, listing_id, new_price):
        """Изменение цены объявления (Администратор/Владелец)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE listings SET price = ? WHERE listing_id = ?", (new_price, listing_id))
        conn.commit()
        conn.close()

    # ===== СДЕЛКИ (DEALS) =====

    def create_deal(self, buyer_telegram_id, listing_id, price):
        """Создание новой сделки (покупка/заказ)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Получаем ID покупателя и продавца
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (buyer_telegram_id,))
            buyer_id = cursor.fetchone()[0]
            
            listing = self.get_listing(listing_id)
            seller_telegram_id = listing[7]
            
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (seller_telegram_id,))
            seller_id = cursor.fetchone()[0]
            
            # 2. Проверяем баланс покупателя
            buyer_data = self.get_user(buyer_telegram_id)
            if buyer_data[5] < price: # balance
                return False, "Недостаточно звезд на балансе"
            
            # 3. Замораживаем средства у покупателя
            cursor.execute("UPDATE users SET balance = balance - ?, frozen_balance = frozen_balance + ? WHERE user_id = ?", 
                          (price, price, buyer_id))
            
            # 4. Создаем сделку
            cursor.execute('''
                INSERT INTO deals (buyer_id, seller_id, listing_id, price, is_frozen)
                VALUES (?, ?, ?, ?, 1)
            ''', (buyer_id, seller_id, listing_id, price))
            deal_id = cursor.lastrowid
            
            conn.commit()
            return True, deal_id, seller_telegram_id
        except Exception as e:
            conn.rollback()
            print(f"Error creating deal: {e}")
            return False, "Ошибка базы данных при создании сделки", None
        finally:
            conn.close()

    def get_deal(self, deal_id):
        """Получение информации о сделке"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,))
        deal = cursor.fetchone()
        conn.close()
        return deal

    def get_user_active_deals(self, telegram_id):
        """Получение активных сделок пользователя (как покупателя или продавца)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (telegram_id,))
        user_id = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT 
                d.deal_id, l.title, d.price, d.status, 
                (SELECT telegram_id FROM users WHERE user_id = d.buyer_id),
                (SELECT telegram_id FROM users WHERE user_id = d.seller_id)
            FROM deals d
            JOIN listings l ON d.listing_id = l.listing_id
            WHERE (d.buyer_id = ? OR d.seller_id = ?) AND d.status IN ('pending', 'accepted', 'arbitration')
            ORDER BY d.created_at DESC
        ''', (user_id, user_id))
        deals = cursor.fetchall()
        conn.close()
        return deals

    def accept_deal(self, deal_id):
        """Продавец принимает сделку"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE deals SET status = 'accepted' WHERE deal_id = ?", (deal_id,))
        conn.commit()
        conn.close()

    def cancel_deal_by_user(self, deal_id):
        """Пользователь отменяет сделку (до принятия)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Получаем данные сделки
            cursor.execute("SELECT buyer_id, price FROM deals WHERE deal_id = ? AND status = 'pending'", (deal_id,))
            deal = cursor.fetchone()
            
            if not deal:
                return False, "Сделка не найдена или уже не в статусе 'pending'"
            
            buyer_id, price = deal
            
            # 2. Размораживаем средства покупателю
            cursor.execute("UPDATE users SET balance = balance + ?, frozen_balance = frozen_balance - ? WHERE user_id = ?", 
                          (price, price, buyer_id))
            
            # 3. Обновляем статус сделки
            cursor.execute("UPDATE deals SET status = 'canceled_by_user', is_frozen = 0 WHERE deal_id = ?", (deal_id,))
            
            conn.commit()
            return True, "Сделка отменена, средства возвращены"
        except Exception as e:
            conn.rollback()
            print(f"Error canceling deal: {e}")
            return False, "Ошибка базы данных при отмене сделки"
        finally:
            conn.close()

    def complete_deal(self, deal_id):
        """Завершение сделки (токены переходят продавцу)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Получаем данные сделки
            cursor.execute("SELECT buyer_id, seller_id, price FROM deals WHERE deal_id = ? AND status = 'accepted'", (deal_id,))
            deal = cursor.fetchone()
            
            if not deal:
                return False, "Сделка не найдена или не в статусе 'accepted'"
            
            buyer_id, seller_id, price = deal
            
            # 2. Списываем замороженные средства у покупателя
            cursor.execute("UPDATE users SET frozen_balance = frozen_balance - ? WHERE user_id = ?", 
                          (price, buyer_id))
            
            # 3. Начисляем средства продавцу
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", 
                          (price, seller_id))
            
            # 4. Обновляем статус сделки
            cursor.execute("UPDATE deals SET status = 'successful', is_frozen = 0 WHERE deal_id = ?", (deal_id,))
            
            conn.commit()
            return True, "Сделка успешно завершена"
        except Exception as e:
            conn.rollback()
            print(f"Error completing deal: {e}")
            return False, "Ошибка базы данных при завершении сделки"
        finally:
            conn.close()

    def start_arbitration(self, deal_id):
        """Начало арбитража (подача жалобы на сделку)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE deals SET status = 'arbitration' WHERE deal_id = ?", (deal_id,))
        conn.commit()
        conn.close()

    def get_arbitration_deals(self):
        """Получение сделок, требующих арбитража"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                d.deal_id, l.title, d.price, 
                (SELECT telegram_id FROM users WHERE user_id = d.buyer_id),
                (SELECT telegram_id FROM users WHERE user_id = d.seller_id)
            FROM deals d
            JOIN listings l ON d.listing_id = l.listing_id
            WHERE d.status = 'arbitration'
            ORDER BY d.created_at ASC
        ''')
        deals = cursor.fetchall()
        conn.close()
        return deals

    def admin_resolve_deal(self, deal_id, action, admin_telegram_id):
        """Разрешение сделки администратором (арбитраж)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Получаем данные сделки
            cursor.execute("SELECT buyer_id, seller_id, price FROM deals WHERE deal_id = ? AND status = 'arbitration'", (deal_id,))
            deal = cursor.fetchone()
            
            if not deal:
                return False, "Сделка не найдена или не в статусе 'arbitration'"
            
            buyer_id, seller_id, price = deal
            
            # 2. Получаем ID администратора
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (admin_telegram_id,))
            admin_id = cursor.fetchone()[0]
            
            if action == 'confirm': # Подтвердить сделку (токены продавцу)
                # Списываем замороженные средства у покупателя
                cursor.execute("UPDATE users SET frozen_balance = frozen_balance - ? WHERE user_id = ?", 
                              (price, buyer_id))
                
                # Начисляем средства продавцу
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", 
                              (price, seller_id))
                
                # Обновляем статус сделки
                cursor.execute("UPDATE deals SET status = 'successful', is_frozen = 0, arbitrator_id = ? WHERE deal_id = ?", 
                              (admin_id, deal_id))
                
                status_text = "подтверждена"
                
            elif action == 'cancel': # Отменить сделку (токены покупателю)
                # Размораживаем средства покупателю (возвращаем на основной баланс)
                cursor.execute("UPDATE users SET balance = balance + ?, frozen_balance = frozen_balance - ? WHERE user_id = ?", 
                              (price, price, buyer_id))
                
                # Обновляем статус сделки
                cursor.execute("UPDATE deals SET status = 'canceled_by_admin', is_frozen = 0, arbitrator_id = ? WHERE deal_id = ?", 
                              (admin_id, deal_id))
                
                status_text = "отменена"
                
            conn.commit()
            return True, status_text
        except Exception as e:
            conn.rollback()
            print(f"Error resolving deal: {e}")
            return False, "Ошибка базы данных при разрешении сделки"
        finally:
            conn.close()

    # ===== ЖАЛОБЫ И РЕЙТИНГ =====

    def add_complaint(self, reporter_telegram_id, target_telegram_id, deal_id, reason):
        """Добавление жалобы"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (reporter_telegram_id,))
            reporter_id = cursor.fetchone()[0]
            
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (target_telegram_id,))
            target_id = cursor.fetchone()[0]
            
            cursor.execute('''
                INSERT INTO complaints (reporter_id, target_id, deal_id, reason)
                VALUES (?, ?, ?, ?)
            ''', (reporter_id, target_id, deal_id, reason))
            complaint_id = cursor.lastrowid
            
            conn.commit()
            return True, complaint_id
        except Exception as e:
            print(f"Error adding complaint: {e}")
            return False, "Ошибка базы данных"
        finally:
            conn.close()

    def get_pending_complaints(self):
        """Получение ожидающих рассмотрения жалоб"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                c.complaint_id, 
                (SELECT telegram_id FROM users WHERE user_id = c.reporter_id),
                (SELECT telegram_id FROM users WHERE user_id = c.target_id),
                c.deal_id, c.reason, c.created_at
            FROM complaints c
            WHERE c.status = 'pending'
            ORDER BY c.created_at ASC
        ''')
        complaints = cursor.fetchall()
        conn.close()
        return complaints

    def resolve_complaint(self, complaint_id, action, admin_telegram_id, rating_change=0):
        """Разрешение жалобы администратором"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Получаем ID администратора
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (admin_telegram_id,))
            admin_id = cursor.fetchone()[0]
            
            # 2. Получаем ID пользователя, на которого жаловались
            cursor.execute("SELECT target_id FROM complaints WHERE complaint_id = ?", (complaint_id,))
            target_id = cursor.fetchone()[0]
            
            status = 'resolved' if action == 'resolve' else 'rejected'
            
            # 3. Обновляем статус жалобы
            cursor.execute('''
                UPDATE complaints SET status = ?, resolved_by = ?
                WHERE complaint_id = ?
            ''', (status, admin_id, complaint_id))
            
            # 4. Обновляем рейтинг и счетчик жалоб, если жалоба разрешена
            if action == 'resolve':
                # Обновляем рейтинг
                cursor.execute("UPDATE users SET rating = rating + ? WHERE user_id = ?", (rating_change, target_id))
                
                # Обновляем счетчик жалоб
                cursor.execute("UPDATE users SET complaints_count = complaints_count + 1 WHERE user_id = ?", (target_id,))
                
                # Проверяем статус аккаунта
                cursor.execute("SELECT complaints_count FROM users WHERE user_id = ?", (target_id,))
                count = cursor.fetchone()[0]
                
                new_status = 'Отличный'
                if count >= 3:
                    new_status = 'На грани блокировки'
                
                cursor.execute("UPDATE users SET status = ? WHERE user_id = ?", (new_status, target_id))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error resolving complaint: {e}")
            return False
        finally:
            conn.close()

    # ===== ЗАЯВКИ НА ПРЕДПРИНИМАТЕЛЯ =====

    def create_entrepreneur_application(self, telegram_id, name, company_name, products_services, about_me, experience):
        """Создание заявки на повышение до Предпринимателя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (telegram_id,))
            user_id = cursor.fetchone()[0]
            
            cursor.execute('''
                INSERT INTO entrepreneur_applications (user_id, name, company_name, products_services, about_me, experience)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, name, company_name, products_services, about_me, experience))
            application_id = cursor.lastrowid
            
            conn.commit()
            return True, application_id
        except Exception as e:
            print(f"Error creating application: {e}")
            return False, "Ошибка базы данных"
        finally:
            conn.close()

    def get_pending_applications(self):
        """Получение ожидающих рассмотрения заявок на Предпринимателя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                a.application_id, u.telegram_id, u.first_name, a.company_name, a.products_services, a.experience, a.created_at
            FROM entrepreneur_applications a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.status = 'pending'
            ORDER BY a.created_at ASC
        ''')
        applications = cursor.fetchall()
        conn.close()
        return applications

    def resolve_application(self, application_id, action, owner_telegram_id):
        """Разрешение заявки на Предпринимателя (Владелец)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Получаем ID владельца
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (owner_telegram_id,))
            owner_id = cursor.fetchone()[0]
            
            # 2. Получаем ID пользователя
            cursor.execute("SELECT user_id FROM entrepreneur_applications WHERE application_id = ?", (application_id,))
            user_id = cursor.fetchone()[0]
            
            # 3. Обновляем статус заявки
            status = 'approved' if action == 'approve' else 'rejected'
            cursor.execute('''
                UPDATE entrepreneur_applications SET status = ?, processed_by = ?
                WHERE application_id = ?
            ''', (status, owner_id, application_id))
            
            # 4. Если одобрено, обновляем роль пользователя
            if action == 'approve':
                cursor.execute("UPDATE users SET role = 'Предприниматель' WHERE user_id = ?", (user_id,))
            
            conn.commit()
            return True, user_id
        except Exception as e:
            conn.rollback()
            print(f"Error resolving application: {e}")
            return False, "Ошибка базы данных"
        finally:
            conn.close()

    # ===== КОНКУРСЫ (CONTESTS) =====

    def add_contest(self, telegram_id, title, description, prize):
        """Добавление нового конкурса"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (telegram_id,))
            user_id = cursor.fetchone()[0]
            
            cursor.execute('''
                INSERT INTO contests (user_id, title, description, prize)
                VALUES (?, ?, ?, ?)
            ''', (user_id, title, description, prize))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding contest: {e}")
            return False
        finally:
            conn.close()

    # ===== ПОСТЫ (РАССЫЛКИ) =====

    def add_post(self, content, telegram_id):
        """Добавление поста (рассылки)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (telegram_id,))
            user_id = cursor.fetchone()[0]
            
            cursor.execute('''
                INSERT INTO posts (content, created_by)
                VALUES (?, ?)
            ''', (content, user_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding post: {e}")
            return False
        finally:
            conn.close()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qarz Boshqaruv Boti - Til o'zgartirish tuzatilgan versiya
"""

import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import io

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

# ==================== KONFIGURATSIYA ====================
TOKEN = "7564758878:AAEaiz7UD2uL4k-2A4bkeTBqABord0aN9FE"
DB_NAME = "debts_bot.db"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
DEBTOR_NAME, AMOUNT, CURRENCY, DUE_DATE, DESCRIPTION, SEARCH, PAYMENT = range(7)

# ==================== TARJIMALAR ====================
TRANSLATIONS = {
    "UZ": {
        "start": "👋 Qarz boshqaruv botiga xush kelibsiz!\n\n📌 Bot orqali qarzlaringizni yozib boring, eslatmalar oling va statistika ko'ring.",
        "menu": "🏠 Asosiy menyu",
        "add_debt": "➕ Qarz qo'shish",
        "debts_list": "📋 Qarzlar ro'yxati",
        "statistics": "📊 Statistika",
        "search": "🔍 Qidiruv",
        "export": "📁 Export",
        "language": "🌐 Til",
        "help": "❓ Yordam",
        "back": "🔙 Orqaga",
        "skip": "⏭️ O'tkazib yuborish",
        "today": "🕐 Bugun",
        "tomorrow": "📅 Ertaga",
        "week": "🗓️ 1 hafta",
        "month": "📆 1 oy",
        "no_date": "❌ Sana yo'q",
        "active_debts": "📗 Aktiv qarzlar",
        "closed_debts": "📕 Yopilgan qarzlar",
        "all_debts": "📘 Barcha qarzlar",
        "close_debt": "✅ Qarzni yopish",
        "partial": "💰 Qisman to'lov",
        "edit": "✏️ Tahrirlash",
        "delete": "🗑️ O'chirish",
        "yes": "✅ Ha",
        "no": "❌ Yo'q",
        "enter_name": "👤 Qarz oluvchi ismini kiriting:",
        "enter_amount": "💰 Summani kiriting:",
        "enter_date": "📅 Qaytarish sanasini tanlang yoki kiriting (DD.MM.YYYY):",
        "enter_desc": "📝 Izoh (ixtiyoriy):",
        "debt_added": "✅ Qarz muvaffaqiyatli qo'shildi!",
        "invalid_amount": "❌ Noto'g'ri summa format. Raqam kiriting.",
        "invalid_date": "❌ Noto'g'ri sana format. DD.MM.YYYY ko'rinishida kiriting.",
        "no_debts": "📭 Qarzlar topilmadi.",
        "debt_info": "📋 Qarz ma'lumotlari:\n👤: {debtor_name}\n💰: {amount} {currency}\n📅: {due_date}\n📝: {description}\n🔄 Holati: {status}\n💵 To'langan: {paid_amount}",
        "stats": "📊 Statistika:\nJami berilgan: {total_given}\nJami olinadigan: {total_to_receive}\nQaytarilishi kerak: {remaining}",
        "enter_search": "🔍 Qidirish uchun so'z yoki raqam kiriting:",
        "search_results": "🔍 Qidiruv natijalari:",
        "select_export": "📁 Export formatini tanlang:",
        "export_success": "✅ Ma'lumotlar {format} formatida eksport qilindi.",
        "lang_changed": "🌐 Til muvaffaqiyatli o'zgartirildi.",
        "reminder_1": "⏰ Eslatma! {debtor_name} ga {amount} {currency} miqdoridagi qarz ertaga ({due_date}) muddati tugaydi.",
        "reminder_3": "⏰ Eslatma! {debtor_name} ga {amount} {currency} miqdoridagi qarz 3 kundan keyin ({due_date}) muddati tugaydi.",
        "due_today": "🚨 Bugun! {debtor_name} ga {amount} {currency} miqdoridagi qarz muddati bugun tugaydi.",
        "enter_payment": "💰 Qancha miqdorda to'lov kiritmoqchisiz?",
        "payment_added": "✅ To'lov muvaffaqiyatli qo'shildi.\nJami to'langan: {paid_amount}\nQolgan: {remaining}",
        "debt_closed": "✅ Qarz yopildi.",
        "confirm_delete": "🗑️ Qarzni o'chirishni tasdiqlaysizmi?",
        "deleted": "🗑️ Qarz o'chirildi.",
        "cancelled": "❌ Amal bekor qilindi.",
        "total": "Jami",
        "active": "Aktiv",
        "closed": "Yopilgan",
        "partial_status": "Qisman to'langan",
        "unknown": "Noma'lum",
        "not_specified": "Ko'rsatilmagan",
        "currency_u": "so'm",
        "currency_r": "руб.",
        "this_month": "Shu oy",
        "last_month": "O'tgan oy",
        "month_stats": "Oy bo'yicha statistika:",
        "select_action": "Tanlang:",
        "or_enter": "Yoki sanani kiriting (DD.MM.YYYY):",
        "or_enter_desc": "Yoki izohni kiriting:",
        "help_text": """🤖 **Qarz Boshqaruv Boti - Yordam**

**Asosiy funksiyalar:**
➕ **Qarz qo'shish** - Yangi qarz qo'shish
📋 **Qarzlar ro'yxati** - Barcha qarzlarni ko'rish
📊 **Statistika** - Umumiy statistikani ko'rish
🔍 **Qidiruv** - Qarzlarni qidirish
📁 **Export** - Ma'lumotlarni yuklab olish (CSV/Excel)
🌐 **Til** - Tilni o'zgartirish

**Qarz holatlari:**
📗 **Aktiv** - Hali to'lanmagan
💰 **Qisman** - Qisman to'langan
📕 **Yopilgan** - To'liq to'langan

**Tezkor tugmalar:**
⏭️ O'tkazib yuborish
🕐 Bugun
📅 Ertaga

**Muammo bo'lsa:**
/cancel - Joriy amalni bekor qilish"""
    },
    "RU": {
        "start": "👋 Добро пожаловать в бот управления долгами!\n\n📌 Записывайте долги, получайте напоминания и смотрите статистику.",
        "menu": "🏠 Главное меню",
        "add_debt": "➕ Добавить долг",
        "debts_list": "📋 Список долгов",
        "statistics": "📊 Статистика",
        "search": "🔍 Поиск",
        "export": "📁 Экспорт",
        "language": "🌐 Язык",
        "help": "❓ Помощь",
        "back": "🔙 Назад",
        "skip": "⏭️ Пропустить",
        "today": "🕐 Сегодня",
        "tomorrow": "📅 Завтра",
        "week": "🗓️ 1 неделя",
        "month": "📆 1 месяц",
        "no_date": "❌ Нет даты",
        "active_debts": "📗 Активные долги",
        "closed_debts": "📕 Закрытые долги",
        "all_debts": "📘 Все долги",
        "close_debt": "✅ Закрыть долг",
        "partial": "💰 Частичный платеж",
        "edit": "✏️ Редактировать",
        "delete": "🗑️ Удалить",
        "yes": "✅ Да",
        "no": "❌ Нет",
        "enter_name": "👤 Введите имя должника:",
        "enter_amount": "💰 Введите сумму:",
        "enter_date": "📅 Выберите дату возврата или введите (ДД.ММ.ГГГГ):",
        "enter_desc": "📝 Описание (необязательно):",
        "debt_added": "✅ Долг успешно добавлен!",
        "invalid_amount": "❌ Неправильный формат суммы. Введите число.",
        "invalid_date": "❌ Неправильный формат даты. Введите в формате ДД.ММ.ГГГГ.",
        "no_debts": "📭 Долги не найдены.",
        "debt_info": "📋 Информация о долге:\n👤: {debtor_name}\n💰: {amount} {currency}\n📅: {due_date}\n📝: {description}\n🔄 Статус: {status}\n💵 Оплачено: {paid_amount}",
        "stats": "📊 Статистика:\nВсего выдано: {total_given}\nВсего к получению: {total_to_receive}\nОсталось получить: {remaining}",
        "enter_search": "🔍 Введите слово или число для поиска:",
        "search_results": "🔍 Результаты поиска:",
        "select_export": "📁 Выберите формат экспорта:",
        "export_success": "✅ Данные экспортированы в формате {format}.",
        "lang_changed": "🌐 Язык успешно изменен.",
        "reminder_1": "⏰ Напоминание! Долг {debtor_name} в размере {amount} {currency} истекает завтра ({due_date}).",
        "reminder_3": "⏰ Напоминание! Долг {debtor_name} в размере {amount} {currency} истекает через 3 дня ({due_date}).",
        "due_today": "🚨 Сегодня! Долг {debtor_name} в размере {amount} {currency} истекает сегодня.",
        "enter_payment": "💰 Какую сумму платежа вы хотите внести?",
        "payment_added": "✅ Платеж успешно добавлен.\nВсего оплачено: {paid_amount}\nОсталось: {remaining}",
        "debt_closed": "✅ Долг закрыт.",
        "confirm_delete": "🗑️ Подтвердите удаление долга?",
        "deleted": "🗑️ Долг удален.",
        "cancelled": "❌ Действие отменено.",
        "total": "Всего",
        "active": "Активный",
        "closed": "Закрыт",
        "partial_status": "Частично оплачен",
        "unknown": "Неизвестно",
        "not_specified": "Не указано",
        "currency_u": "сум",
        "currency_r": "руб.",
        "this_month": "Этот месяц",
        "last_month": "Прошлый месяц",
        "month_stats": "Статистика по месяцам:",
        "select_action": "Выберите:",
        "or_enter": "Или введите дату (ДД.ММ.ГГГГ):",
        "or_enter_desc": "Или введите описание:",
        "help_text": """🤖 **Бот управления долгами - Помощь**

**Основные функции:**
➕ **Добавить долг** - Добавить новый долг
📋 **Список долгов** - Просмотреть все долги
📊 **Статистика** - Просмотреть общую статистику
🔍 **Поиск** - Поиск долгов
📁 **Экспорт** - Скачать данные (CSV/Excel)
🌐 **Язык** - Изменить язык

**Статусы долгов:**
📗 **Активный** - Еще не оплачен
💰 **Частичный** - Частично оплачен
📕 **Закрыт** - Полностью оплачен

**Быстрые кнопки:**
⏭️ Пропустить
🕐 Сегодня
📅 Завтра

**При проблемах:**
/cancel - Отменить текущее действие"""
    },
    "EN": {
        "start": "👋 Welcome to the Debt Management Bot!\n\n📌 Record your debts, get reminders, and view statistics.",
        "menu": "🏠 Main Menu",
        "add_debt": "➕ Add Debt",
        "debts_list": "📋 Debts List",
        "statistics": "📊 Statistics",
        "search": "🔍 Search",
        "export": "📁 Export",
        "language": "🌐 Language",
        "help": "❓ Help",
        "back": "🔙 Back",
        "skip": "⏭️ Skip",
        "today": "🕐 Today",
        "tomorrow": "📅 Tomorrow",
        "week": "🗓️ 1 week",
        "month": "📆 1 month",
        "no_date": "❌ No date",
        "active_debts": "📗 Active Debts",
        "closed_debts": "📕 Closed Debts",
        "all_debts": "📘 All Debts",
        "close_debt": "✅ Close Debt",
        "partial": "💰 Partial Payment",
        "edit": "✏️ Edit",
        "delete": "🗑️ Delete",
        "yes": "✅ Yes",
        "no": "❌ No",
        "enter_name": "👤 Enter debtor name:",
        "enter_amount": "💰 Enter amount:",
        "enter_date": "📅 Select due date or enter (DD.MM.YYYY):",
        "enter_desc": "📝 Description (optional):",
        "debt_added": "✅ Debt successfully added!",
        "invalid_amount": "❌ Invalid amount format. Enter a number.",
        "invalid_date": "❌ Invalid date format. Enter in DD.MM.YYYY format.",
        "no_debts": "📭 No debts found.",
        "debt_info": "📋 Debt Information:\n👤: {debtor_name}\n💰: {amount} {currency}\n📅: {due_date}\n📝: {description}\n🔄 Status: {status}\n💵 Paid: {paid_amount}",
        "stats": "📊 Statistics:\nTotal Given: {total_given}\nTotal to Receive: {total_to_receive}\nRemaining: {remaining}",
        "enter_search": "🔍 Enter word or number to search:",
        "search_results": "🔍 Search results:",
        "select_export": "📁 Select export format:",
        "export_success": "✅ Data exported in {format} format.",
        "lang_changed": "🌐 Language successfully changed.",
        "reminder_1": "⏰ Reminder! Debt to {debtor_name} of {amount} {currency} is due tomorrow ({due_date}).",
        "reminder_3": "⏰ Reminder! Debt to {debtor_name} of {amount} {currency} is due in 3 days ({due_date}).",
        "due_today": "🚨 Today! Debt to {debtor_name} of {amount} {currency} is due today.",
        "enter_payment": "💰 How much payment do you want to add?",
        "payment_added": "✅ Payment successfully added.\nTotal paid: {paid_amount}\nRemaining: {remaining}",
        "debt_closed": "✅ Debt closed.",
        "confirm_delete": "🗑️ Confirm debt deletion?",
        "deleted": "🗑️ Debt deleted.",
        "cancelled": "❌ Action cancelled.",
        "total": "Total",
        "active": "Active",
        "closed": "Closed",
        "partial_status": "Partial",
        "unknown": "Unknown",
        "not_specified": "Not specified",
        "currency_u": "UZS",
        "currency_r": "RUB",
        "this_month": "This month",
        "last_month": "Last month",
        "month_stats": "Monthly statistics:",
        "select_action": "Select:",
        "or_enter": "Or enter date (DD.MM.YYYY):",
        "or_enter_desc": "Or enter description:",
        "help_text": """🤖 **Debt Management Bot - Help**

**Main functions:**
➕ **Add Debt** - Add new debt
📋 **Debts List** - View all debts
📊 **Statistics** - View overall statistics
🔍 **Search** - Search debts
📁 **Export** - Download data (CSV/Excel)
🌐 **Language** - Change language

**Debt statuses:**
📗 **Active** - Not paid yet
💰 **Partial** - Partially paid
📕 **Closed** - Fully paid

**Quick buttons:**
⏭️ Skip
🕐 Today
📅 Tomorrow

**If you have problems:**
/cancel - Cancel current action"""
    }
}

def get_text(key: str, lang: str = "UZ") -> str:
    """Tarjima olish"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["UZ"]).get(key, key)

# ==================== BAZA ====================
class Database:
    def __init__(self, db_name: str = DB_NAME):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()
    
    def init_db(self):
        """Bazani yaratish"""
        # Foydalanuvchilar
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'UZ',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Qarzlar
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS debts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                debtor_name TEXT NOT NULL,
                amount REAL NOT NULL,
                paid_amount REAL DEFAULT 0,
                currency TEXT DEFAULT 'UZS',
                due_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                description TEXT,
                group_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        self.conn.commit()
        logger.info("Database initialized")
    
    def add_user(self, user_id: int, username: str = None, 
                 first_name: str = None, last_name: str = None, 
                 language: str = "UZ"):
        """Foydalanuvchi qo'shish"""
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, language)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, first_name, last_name, language))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Foydalanuvchini olish"""
        try:
            self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = self.cursor.fetchone()
            if row:
                columns = [desc[0] for desc in self.cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def update_user_language(self, user_id: int, language: str):
        """Foydalanuvchi tilini yangilash"""
        try:
            self.cursor.execute(
                "UPDATE users SET language = ? WHERE user_id = ?",
                (language, user_id)
            )
            self.conn.commit()
            logger.info(f"User {user_id} language updated to {language}")
            return True
        except Exception as e:
            logger.error(f"Error updating language: {e}")
            return False
    
    def add_debt(self, user_id: int, debtor_name: str, amount: float,
                 currency: str = "UZS", due_date: str = None,
                 description: str = None, group_id: int = None) -> Optional[int]:
        """Qarz qo'shish"""
        try:
            self.cursor.execute("""
                INSERT INTO debts 
                (user_id, debtor_name, amount, currency, due_date, description, group_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, debtor_name, amount, currency, due_date, description, group_id))
            debt_id = self.cursor.lastrowid
            self.conn.commit()
            logger.info(f"Debt added: ID={debt_id}")
            return debt_id
        except Exception as e:
            logger.error(f"Error adding debt: {e}")
            return None
    
    def get_debts(self, user_id: int, status: str = None) -> List[Dict]:
        """Qarzlarni olish"""
        try:
            query = "SELECT * FROM debts WHERE user_id = ?"
            params = [user_id]
            
            if status and status != "all":
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY due_date ASC, created_at DESC"
            
            self.cursor.execute(query, tuple(params))
            rows = self.cursor.fetchall()
            
            if rows:
                columns = [desc[0] for desc in self.cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            return []
        except Exception as e:
            logger.error(f"Error getting debts: {e}")
            return []
    
    def get_debt(self, debt_id: int, user_id: int = None) -> Optional[Dict]:
        """Bitta qarzni olish"""
        try:
            query = "SELECT * FROM debts WHERE id = ?"
            params = [debt_id]
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            self.cursor.execute(query, tuple(params))
            row = self.cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in self.cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"Error getting debt: {e}")
            return None
    
    def update_debt_status(self, debt_id: int, status: str, 
                          paid_amount: float = None, user_id: int = None):
        """Qarz holatini yangilash"""
        try:
            if paid_amount is not None:
                query = "UPDATE debts SET status = ?, paid_amount = ? WHERE id = ?"
                params = [status, paid_amount, debt_id]
            else:
                query = "UPDATE debts SET status = ? WHERE id = ?"
                params = [status, debt_id]
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            self.cursor.execute(query, tuple(params))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating debt status: {e}")
            return False
    
    def partial_payment(self, debt_id: int, amount: float, user_id: int = None):
        """Qisman to'lov"""
        try:
            debt = self.get_debt(debt_id, user_id)
            if not debt:
                return False
            
            new_paid = debt["paid_amount"] + amount
            status = "closed" if new_paid >= debt["amount"] else "partial"
            
            self.cursor.execute("""
                UPDATE debts 
                SET paid_amount = ?, status = ?
                WHERE id = ? AND user_id = ?
            """, (new_paid, status, debt_id, user_id or debt["user_id"]))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding partial payment: {e}")
            return False
    
    def delete_debt(self, debt_id: int, user_id: int = None):
        """Qarzni o'chirish"""
        try:
            query = "DELETE FROM debts WHERE id = ?"
            params = [debt_id]
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            self.cursor.execute(query, tuple(params))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting debt: {e}")
            return False
    
    def search_debts(self, user_id: int, search_term: str) -> List[Dict]:
        """Qidiruv"""
        try:
            self.cursor.execute("""
                SELECT * FROM debts 
                WHERE user_id = ? 
                AND (debtor_name LIKE ? OR description LIKE ? OR CAST(amount AS TEXT) LIKE ?)
                ORDER BY created_at DESC
            """, (user_id, f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            
            rows = self.cursor.fetchall()
            if rows:
                columns = [desc[0] for desc in self.cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            return []
        except Exception as e:
            logger.error(f"Error searching debts: {e}")
            return []
    
    def get_statistics(self, user_id: int) -> Dict:
        """Statistika"""
        try:
            # Jami berilgan
            self.cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM debts WHERE user_id = ?",
                (user_id,)
            )
            total_given = self.cursor.fetchone()[0] or 0
            
            # Jami olinadigan
            self.cursor.execute("""
                SELECT COALESCE(SUM(amount - paid_amount), 0) 
                FROM debts 
                WHERE user_id = ? AND status != 'closed'
            """, (user_id,))
            total_to_receive = self.cursor.fetchone()[0] or 0
            
            # Oy bo'yicha
            self.cursor.execute("""
                SELECT 
                    strftime('%Y-%m', created_at) as month,
                    COUNT(*) as count,
                    SUM(amount) as total_amount,
                    SUM(amount - paid_amount) as remaining
                FROM debts 
                WHERE user_id = ?
                GROUP BY strftime('%Y-%m', created_at)
                ORDER BY month DESC
                LIMIT 6
            """, (user_id,))
            
            monthly_stats = self.cursor.fetchall()
            
            return {
                "total_given": total_given,
                "total_to_receive": total_to_receive,
                "monthly_stats": monthly_stats
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"total_given": 0, "total_to_receive": 0, "monthly_stats": []}
    
    def close(self):
        """Bazani yopish"""
        self.conn.close()

db = Database()

# ==================== KLAVIATURALAR ====================
def get_main_keyboard(lang: str = "UZ") -> ReplyKeyboardMarkup:
    """Asosiy klaviatura"""
    keyboard = [
        [get_text("add_debt", lang)],
        [get_text("debts_list", lang), get_text("statistics", lang)],
        [get_text("search", lang), get_text("export", lang)],
        [get_text("language", lang), get_text("help", lang)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_skip_keyboard(lang: str = "UZ") -> ReplyKeyboardMarkup:
    """Skip tugmasi bilan klaviatura"""
    keyboard = [[get_text("skip", lang)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_date_keyboard(lang: str = "UZ") -> ReplyKeyboardMarkup:
    """Sana tanlash uchun klaviatura"""
    keyboard = [
        [get_text("today", lang), get_text("tomorrow", lang)],
        [get_text("week", lang), get_text("month", lang)],
        [get_text("skip", lang)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_debts_keyboard(lang: str = "UZ") -> InlineKeyboardMarkup:
    """Qarzlar ro'yxati klaviaturasi"""
    keyboard = [
        [
            InlineKeyboardButton(get_text("active_debts", lang), callback_data="debts_active"),
            InlineKeyboardButton(get_text("closed_debts", lang), callback_data="debts_closed")
        ],
        [
            InlineKeyboardButton(get_text("all_debts", lang), callback_data="debts_all"),
            InlineKeyboardButton(get_text("back", lang), callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_debt_actions_keyboard(debt_id: int, lang: str = "UZ") -> InlineKeyboardMarkup:
    """Qarz amallari klaviaturasi"""
    keyboard = [
        [
            InlineKeyboardButton(get_text("close_debt", lang), callback_data=f"close_{debt_id}"),
            InlineKeyboardButton(get_text("partial", lang), callback_data=f"partial_{debt_id}")
        ],
        [
            InlineKeyboardButton(get_text("edit", lang), callback_data=f"edit_{debt_id}"),
            InlineKeyboardButton(get_text("delete", lang), callback_data=f"delete_{debt_id}")
        ],
        [InlineKeyboardButton(get_text("back", lang), callback_data="debts_list")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_currency_keyboard(lang: str = "UZ") -> InlineKeyboardMarkup:
    """Valyuta klaviaturasi"""
    keyboard = [
        [
            InlineKeyboardButton("🇺🇿 UZS", callback_data="currency_UZS"),
            InlineKeyboardButton("🇺🇸 USD", callback_data="currency_USD"),
            InlineKeyboardButton("🇪🇺 EUR", callback_data="currency_EUR")
        ],
        [
            InlineKeyboardButton("🇷🇺 RUB", callback_data="currency_RUB"),
            InlineKeyboardButton(get_text("back", lang), callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Til klaviaturasi"""
    keyboard = [
        [
            InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_UZ"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_RU"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_EN")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_export_keyboard(lang: str = "UZ") -> InlineKeyboardMarkup:
    """Export klaviaturasi"""
    keyboard = [
        [
            InlineKeyboardButton("CSV", callback_data="export_csv"),
            InlineKeyboardButton("Excel", callback_data="export_excel")
        ],
        [InlineKeyboardButton(get_text("back", lang), callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard(action: str, debt_id: int, lang: str = "UZ") -> InlineKeyboardMarkup:
    """Tasdiqlash klaviaturasi"""
    keyboard = [
        [
            InlineKeyboardButton(get_text("yes", lang), callback_data=f"confirm_{action}_{debt_id}"),
            InlineKeyboardButton(get_text("no", lang), callback_data=f"cancel_{action}_{debt_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard(callback_data: str, lang: str = "UZ") -> InlineKeyboardMarkup:
    """Orqaga klaviaturasi"""
    keyboard = [
        [InlineKeyboardButton(get_text("back", lang), callback_data=callback_data)]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== BOT HANDLERLARI ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi"""
    user = update.effective_user
    
    # Foydalanuvchini bazaga qo'shish
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Foydalanuvchi tilini olish
    user_data = db.get_user(user.id)
    lang = user_data["language"] if user_data else "UZ"
    
    await update.message.reply_text(
        get_text("start", lang),
        reply_markup=get_main_keyboard(lang),
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asosiy menyu"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    await query.message.reply_text(
        get_text("menu", lang),
        reply_markup=get_main_keyboard(lang),
        parse_mode=ParseMode.MARKDOWN
    )

async def add_debt_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qarz qo'shishni boshlash"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    await update.message.reply_text(
        get_text("enter_name", lang),
        reply_markup=ReplyKeyboardRemove()
    )
    return DEBTOR_NAME

async def get_debtor_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qarz oluvchi ismini olish"""
    context.user_data["debtor_name"] = update.message.text
    
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    await update.message.reply_text(get_text("enter_amount", lang))
    return AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Summani olish"""
    try:
        amount = float(update.message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        context.user_data["amount"] = amount
        
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        lang = user_data["language"] if user_data else "UZ"
        
        await update.message.reply_text(
            "💱 Valyutani tanlang:",
            reply_markup=get_currency_keyboard(lang)
        )
        return CURRENCY
    except ValueError:
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        lang = user_data["language"] if user_data else "UZ"
        
        await update.message.reply_text(get_text("invalid_amount", lang))
        return AMOUNT

async def get_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Valyutani olish"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await cancel_conversation(update, context)
        return ConversationHandler.END
    
    currency = query.data.split("_")[1]
    context.user_data["currency"] = currency
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    await query.message.reply_text(
        f"{get_text('enter_date', lang)}\n\n{get_text('or_enter', lang)}",
        reply_markup=get_date_keyboard(lang)
    )
    return DUE_DATE

async def get_due_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muddatni olish"""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    # Klaviatura tugmalarini tekshirish
    if text == get_text("skip", lang):
        context.user_data["due_date"] = None
    elif text == get_text("today", lang):
        date_obj = datetime.now()
        context.user_data["due_date"] = date_obj.strftime("%Y-%m-%d")
    elif text == get_text("tomorrow", lang):
        date_obj = datetime.now() + timedelta(days=1)
        context.user_data["due_date"] = date_obj.strftime("%Y-%m-%d")
    elif text == get_text("week", lang):
        date_obj = datetime.now() + timedelta(days=7)
        context.user_data["due_date"] = date_obj.strftime("%Y-%m-%d")
    elif text == get_text("month", lang):
        date_obj = datetime.now() + timedelta(days=30)
        context.user_data["due_date"] = date_obj.strftime("%Y-%m-%d")
    else:
        # Foydalanuvchi sanani o'zi kiritgan
        try:
            date_obj = datetime.strptime(text, "%d.%m.%Y")
            if date_obj.date() < datetime.now().date():
                await update.message.reply_text(
                    "❌ Sana o'tgan bo'lishi mumkin emas!",
                    reply_markup=get_date_keyboard(lang)
                )
                return DUE_DATE
            context.user_data["due_date"] = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            await update.message.reply_text(
                f"{get_text('invalid_date', lang)}\n\n{get_text('or_enter', lang)}",
                reply_markup=get_date_keyboard(lang)
            )
            return DUE_DATE
    
    await update.message.reply_text(
        f"{get_text('enter_desc', lang)}\n\n{get_text('or_enter_desc', lang)}",
        reply_markup=get_skip_keyboard(lang)
    )
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Izohni olish"""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    if text == get_text("skip", lang):
        context.user_data["description"] = None
    else:
        context.user_data["description"] = text
    
    # Qarzni saqlash
    debt_id = db.add_debt(
        user_id=user_id,
        debtor_name=context.user_data["debtor_name"],
        amount=context.user_data["amount"],
        currency=context.user_data.get("currency", "UZS"),
        due_date=context.user_data.get("due_date"),
        description=context.user_data.get("description")
    )
    
    if debt_id:
        success_message = f"""
✅ **{get_text('debt_added', lang)}**

👤 **{get_text('enter_name', lang).split(':')[0]}:** {context.user_data['debtor_name']}
💰 **{get_text('enter_amount', lang).split(':')[0]}:** {context.user_data['amount']} {context.user_data.get('currency', 'UZS')}
"""
        
        if context.user_data.get('due_date'):
            due_date = datetime.strptime(context.user_data['due_date'], "%Y-%m-%d").strftime("%d.%m.%Y")
            success_message += f"📅 **{get_text('enter_date', lang).split(':')[0]}:** {due_date}\n"
        
        if context.user_data.get('description'):
            success_message += f"📝 **{get_text('enter_desc', lang).split(':')[0]}:** {context.user_data['description']}\n"
        
        success_message += f"\n🆔 **ID:** {debt_id}"
        
        await update.message.reply_text(
            success_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(lang)
        )
    else:
        await update.message.reply_text(
            "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=get_main_keyboard(lang)
        )
    
    # Tozalash
    context.user_data.clear()
    return ConversationHandler.END

async def show_debts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qarzlar menyusi"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    if update.message:
        await update.message.reply_text(
            "📋 Qarzlar ro'yxati:",
            reply_markup=get_debts_keyboard(lang)
        )
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "📋 Qarzlar ro'yxati:",
            reply_markup=get_debts_keyboard(lang)
        )

async def show_debts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qarzlarni ko'rsatish"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    status = query.data.split("_")[1]
    
    if status == "all":
        debts = db.get_debts(user_id)
        title = get_text("all_debts", lang)
    else:
        debts = db.get_debts(user_id, status=status)
        title = get_text("active_debts", lang) if status == "active" else get_text("closed_debts", lang)
    
    if not debts:
        await query.edit_message_text(
            get_text("no_debts", lang),
            reply_markup=get_back_keyboard("debts_list", lang)
        )
        return
    
    message = f"**{title}:**\n\n"
    
    for i, debt in enumerate(debts[:20], 1):
        due_date = debt.get("due_date")
        if due_date:
            try:
                due_date = datetime.strptime(due_date, "%Y-%m-%d").strftime("%d.%m.%Y")
            except:
                pass
        else:
            due_date = get_text("no_date", lang)
        
        status_text = get_text("active", lang) if debt["status"] == "active" else get_text("closed", lang) if debt["status"] == "closed" else get_text("partial_status", lang)
        
        message += f"**{i}. {debt['debtor_name']}** - {debt['amount']} {debt['currency']}\n"
        message += f"📅 {due_date} | 🔄 {status_text}\n"
        
        if debt["description"]:
            desc = debt["description"][:30] + "..." if len(debt["description"]) > 30 else debt["description"]
            message += f"📝 {desc}\n"
        
        if debt["status"] != "closed":
            remaining = debt['amount'] - debt['paid_amount']
            message += f"💰 {remaining} {debt['currency']} qolgan\n"
        
        message += f"🆔 {debt['id']}\n\n"
    
    if len(debts) > 20:
        message += f"\n... va yana {len(debts) - 20} ta qarz"
    
    keyboard = []
    for debt in debts[:5]:
        keyboard.append([
            InlineKeyboardButton(
                f"{debt['debtor_name']} - {debt['amount']} {debt['currency']}",
                callback_data=f"details_{debt['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(get_text("back", lang), callback_data="debts_list")])
    
    await query.edit_message_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_debt_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qarz tafsilotlari"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    debt_id = int(query.data.split("_")[1])
    
    debt = db.get_debt(debt_id, user_id)
    if not debt:
        await query.edit_message_text("❌ Qarz topilmadi!")
        return
    
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    due_date = debt.get("due_date")
    if due_date:
        try:
            due_date = datetime.strptime(due_date, "%Y-%m-%d").strftime("%d.%m.%Y")
        except:
            pass
    else:
        due_date = get_text("no_date", lang)
    
    status_text = get_text("active", lang) if debt["status"] == "active" else get_text("closed", lang) if debt["status"] == "closed" else get_text("partial_status", lang)
    
    message = f"""
📋 **{get_text('debt_info', lang).split(':')[0]}:**

👤 **{get_text('enter_name', lang).split(':')[0]}:** {debt['debtor_name']}
💰 **{get_text('enter_amount', lang).split(':')[0]}:** {debt['amount']} {debt['currency']}
📅 **{get_text('enter_date', lang).split(':')[0]}:** {due_date}
📝 **{get_text('enter_desc', lang).split(':')[0]}:** {debt['description'] or get_text('not_specified', lang)}
🔄 **Holati:** {status_text}
💵 **{get_text('payment_added', lang).split(':')[0]}:** {debt['paid_amount']} {debt['currency']}
"""
    
    if debt["status"] != "closed":
        remaining = debt['amount'] - debt['paid_amount']
        message += f"⏳ **Qolgan:** {remaining} {debt['currency']}\n"
    
    message += f"\n🆔 **ID:** {debt['id']}"
    
    if debt["status"] != "closed":
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_debt_actions_keyboard(debt_id, lang)
        )
    else:
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard("debts_list", lang)
        )

async def close_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qarzni yopish"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    debt_id = int(query.data.split("_")[1])
    
    debt = db.get_debt(debt_id, user_id)
    if not debt:
        await query.edit_message_text("❌ Qarz topilmadi!")
        return
    
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    db.update_debt_status(debt_id, "closed", debt["amount"], user_id)
    
    await query.edit_message_text(
        get_text("debt_closed", lang),
        reply_markup=get_back_keyboard("debts_list", lang)
    )

async def start_partial_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qisman to'lov boshlash"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    debt_id = int(query.data.split("_")[1])
    
    context.user_data["partial_debt_id"] = debt_id
    
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    debt = db.get_debt(debt_id, user_id)
    if debt:
        remaining = debt['amount'] - debt['paid_amount']
        await query.message.reply_text(
            f"💰 {get_text('enter_payment', lang)}\n\n"
            f"Jami qarz: {debt['amount']} {debt['currency']}\n"
            f"To'langan: {debt['paid_amount']} {debt['currency']}\n"
            f"Qolgan: {remaining} {debt['currency']}",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await query.message.reply_text(get_text("enter_payment", lang))
    
    return PAYMENT

async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """To'lovni qayta ishlash"""
    try:
        amount = float(update.message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
        
        debt_id = context.user_data.get("partial_debt_id")
        
        if not debt_id:
            return ConversationHandler.END
        
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        lang = user_data["language"] if user_data else "UZ"
        
        success = db.partial_payment(debt_id, amount, user_id)
        
        if success:
            debt = db.get_debt(debt_id, user_id)
            await update.message.reply_text(
                get_text("payment_added", lang).format(
                    paid_amount=debt["paid_amount"],
                    remaining=debt["amount"] - debt["paid_amount"]
                ),
                reply_markup=get_main_keyboard(lang)
            )
        else:
            await update.message.reply_text(
                "❌ Xatolik yuz berdi!",
                reply_markup=get_main_keyboard(lang)
            )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        lang = user_data["language"] if user_data else "UZ"
        
        await update.message.reply_text(get_text("invalid_amount", lang))
        return PAYMENT

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'chirishni tasdiqlash"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    debt_id = int(query.data.split("_")[1])
    
    context.user_data["delete_debt_id"] = debt_id
    
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    await query.edit_message_text(
        get_text("confirm_delete", lang),
        reply_markup=get_confirmation_keyboard("delete", debt_id, lang)
    )

async def delete_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qarzni o'chirish"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    debt_id = int(query.data.split("_")[2])
    
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    if query.data.startswith("confirm"):
        success = db.delete_debt(debt_id, user_id)
        if success:
            await query.edit_message_text(
                get_text("deleted", lang),
                reply_markup=get_back_keyboard("debts_list", lang)
            )
        else:
            await query.edit_message_text(
                "❌ Xatolik yuz berdi!",
                reply_markup=get_back_keyboard("debts_list", lang)
            )
    else:
        await query.edit_message_text(
            get_text("cancelled", lang),
            reply_markup=get_back_keyboard("debts_list", lang)
        )

async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistika"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    stats = db.get_statistics(user_id)
    
    message = f"""
📊 **{get_text('stats', lang).split(':')[0]}:**

💰 **Jami berilgan:** {stats["total_given"]:,.0f} so'm
📈 **Jami olinadigan:** {stats["total_to_receive"]:,.0f} so'm
⏳ **Qaytarilishi kerak:** {stats["total_given"] - stats["total_to_receive"]:,.0f} so'm
"""
    
    if stats["monthly_stats"]:
        message += f"\n📅 **{get_text('month_stats', lang)}**\n"
        for month_stat in stats["monthly_stats"]:
            month, count, total, remaining = month_stat
            try:
                month_name = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
            except:
                month_name = month
            
            message += f"\n**{month_name}:**\n"
            message += f"   📊 {get_text('total', lang)}: {count} ta\n"
            message += f"   💰 {get_text('total', lang)}: {total:,.0f} so'm\n"
            message += f"   ⏳ {get_text('total', lang)}: {remaining:,.0f} so'm\n"
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(lang)
    )

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qidiruvni boshlash"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    await update.message.reply_text(
        get_text("enter_search", lang),
        reply_markup=ReplyKeyboardRemove()
    )
    return SEARCH

async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qidiruvni qayta ishlash"""
    search_term = update.message.text
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    results = db.search_debts(user_id, search_term)
    
    if not results:
        await update.message.reply_text(
            get_text("no_debts", lang),
            reply_markup=get_main_keyboard(lang)
        )
        return ConversationHandler.END
    
    message = f"**{get_text('search_results', lang)} '{search_term}':**\n\n"
    
    for i, debt in enumerate(results[:10], 1):
        due_date = debt.get("due_date")
        if due_date:
            try:
                due_date = datetime.strptime(due_date, "%Y-%m-%d").strftime("%d.%m.%Y")
            except:
                pass
        else:
            due_date = get_text("no_date", lang)
        
        status_text = get_text("active", lang) if debt["status"] == "active" else get_text("closed", lang) if debt["status"] == "closed" else get_text("partial_status", lang)
        
        message += f"**{i}. {debt['debtor_name']}** - {debt['amount']} {debt['currency']}\n"
        message += f"📅 {due_date} | 🔄 {status_text}\n"
        
        if debt["description"]:
            desc = debt["description"][:30] + "..." if len(debt["description"]) > 30 else debt["description"]
            message += f"📝 {desc}\n"
        
        message += f"🆔 {debt['id']}\n\n"
    
    if len(results) > 10:
        message += f"\n... va yana {len(results) - 10} ta natija"
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(lang)
    )
    
    return ConversationHandler.END

async def show_export_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export menyusi"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    await update.message.reply_text(
        get_text("select_export", lang),
        reply_markup=get_export_keyboard(lang)
    )

async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ma'lumotlarni export qilish"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    export_type = query.data.split("_")[1]
    
    try:
        debts = db.get_debts(user_id, status="all")
        if not debts:
            await query.edit_message_text(
                get_text("no_debts", lang),
                reply_markup=get_back_keyboard("main_menu", lang)
            )
            return
        
        # CSV yaratish
        if export_type == "csv":
            data = []
            for debt in debts:
                row = {
                    'ID': debt['id'],
                    'Qarz oluvchi': debt['debtor_name'],
                    'Summa': debt['amount'],
                    "To'langan": debt['paid_amount'],
                    'Qolgan': debt['amount'] - debt['paid_amount'],
                    'Valyuta': debt['currency'],
                    'Muddati': debt.get('due_date', ''),
                    'Holati': debt['status'],
                    'Izoh': debt['description'] or '',
                    'Yaratilgan sana': debt.get('created_at', '')
                }
                data.append(row)
            
            df = pd.DataFrame(data)
            output = io.BytesIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')
            output.seek(0)
            
            await context.bot.send_document(
                chat_id=user_id,
                document=output,
                filename="qarzlar.csv",
                caption=get_text("export_success", lang).format(format="CSV")
            )
        
        # Excel yaratish
        elif export_type == "excel":
            data = []
            for debt in debts:
                row = {
                    'ID': debt['id'],
                    'Qarz oluvchi': debt['debtor_name'],
                    'Summa': float(debt['amount']),
                    "To'langan": float(debt['paid_amount']),
                    'Qolgan': float(debt['amount'] - debt['paid_amount']),
                    'Valyuta': debt['currency'],
                    'Muddati': debt.get('due_date', ''),
                    'Holati': debt['status'],
                    'Izoh': debt['description'] or '',
                    'Yaratilgan sana': debt.get('created_at', '')
                }
                data.append(row)
            
            df = pd.DataFrame(data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Qarzlar')
                worksheet = writer.sheets['Qarzlar']
                
                # Ustun kengliklarini sozlash
                column_widths = {'A': 8, 'B': 20, 'C': 12, 'D': 12, 'E': 12,
                               'F': 10, 'G': 12, 'H': 12, 'I': 30, 'J': 15}
                for col, width in column_widths.items():
                    worksheet.column_dimensions[col].width = width
            
            output.seek(0)
            
            await context.bot.send_document(
                chat_id=user_id,
                document=output,
                filename="qarzlar.xlsx",
                caption=get_text("export_success", lang).format(format="Excel")
            )
        
        await query.edit_message_text(
            get_text("export_success", lang).format(format=export_type.upper()),
            reply_markup=get_back_keyboard("main_menu", lang)
        )
    
    except Exception as e:
        logger.error(f"Export error: {e}")
        await query.edit_message_text(
            f"❌ Export qilishda xatolik: {str(e)}",
            reply_markup=get_back_keyboard("main_menu", lang)
        )

async def show_language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Til menyusi"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    await update.message.reply_text(
        "🌐 Tilni tanlang / Select language / Выберите язык:",
        reply_markup=get_language_keyboard()
    )

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tilni o'zgartirish - BU ASOSIY FUNKSIYA!"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = query.data.split("_")[1]  # lang_UZ -> UZ, lang_RU -> RU, lang_EN -> EN
    
    logger.info(f"Changing language for user {user_id} to {lang_code}")
    
    # Tilni bazada yangilash
    success = db.update_user_language(user_id, lang_code)
    
    if success:
        logger.info(f"Language updated successfully for user {user_id}")
        
        # Yangi tilga o'tish xabarini yuborish
        await query.message.reply_text(
            get_text("lang_changed", lang_code),
            reply_markup=get_main_keyboard(lang_code)
        )
        
        # Eski xabarni yangilash (agar kerak bo'lsa)
        try:
            await query.edit_message_text(
                f"🌐 {get_text('lang_changed', lang_code)}",
                reply_markup=None
            )
        except:
            pass
    else:
        logger.error(f"Failed to update language for user {user_id}")
        await query.message.reply_text(
            "❌ Tilni o'zgartirishda xatolik yuz berdi.",
            reply_markup=get_main_keyboard("UZ")
        )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    await update.message.reply_text(
        get_text("help_text", lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(lang)
    )

async def cancel_conversation(update, context: ContextTypes.DEFAULT_TYPE):
    """Conversationni bekor qilish"""
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    
    if update.message:
        await update.message.reply_text(
            get_text("cancelled", lang),
            reply_markup=get_main_keyboard(lang)
        )
    else:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(
            get_text("cancelled", lang),
            reply_markup=get_main_keyboard(lang)
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matnli xabarlarni qayta ishlash"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    lang = user_data["language"] if user_data else "UZ"
    text = update.message.text
    
    # Klaviatura tugmalarini tekshirish
    if text == get_text("add_debt", lang):
        await add_debt_start(update, context)
    elif text == get_text("debts_list", lang):
        await show_debts_menu(update, context)
    elif text == get_text("statistics", lang):
        await show_statistics(update, context)
    elif text == get_text("search", lang):
        await start_search(update, context)
    elif text == get_text("export", lang):
        await show_export_menu(update, context)
    elif text == get_text("language", lang):
        await show_language_menu(update, context)
    elif text == get_text("help", lang):
        await show_help(update, context)
    else:
        # Agar xabar tugma emas, boshqa handlerlarga yo'naltirish
        await update.message.reply_text(
            "🤔 Tushunmadim. Iltimos, menyudan birini tanlang.",
            reply_markup=get_main_keyboard(lang)
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xatolarni qayta ishlash"""
    logger.error(f"Xatolik: {context.error}", exc_info=context.error)

# ==================== ASOSIY FUNKSIYA ====================
def main():
    """Asosiy funksiya"""
    # Bot ilovasini yaratish
    application = Application.builder().token(TOKEN).build()
    
    # Xatolik handleri
    application.add_error_handler(error_handler)
    
    # Conversation handler for adding debt
    add_debt_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r'^➕.*$'), add_debt_start),
            CommandHandler("add", add_debt_start)
        ],
        states={
            DEBTOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_debtor_name)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
            CURRENCY: [CallbackQueryHandler(get_currency, pattern=r'^currency_|^cancel$')],
            DUE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_due_date)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            MessageHandler(filters.COMMAND, cancel_conversation)
        ]
    )
    
    # Conversation handler for search
    search_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r'^🔍.*$'), start_search),
            CommandHandler("search", start_search)
        ],
        states={
            SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_search)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            MessageHandler(filters.COMMAND, cancel_conversation)
        ]
    )
    
    # Conversation handler for partial payment
    payment_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_partial_payment, pattern=r'^partial_\d+$')
        ],
        states={
            PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_payment)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            MessageHandler(filters.COMMAND, cancel_conversation)
        ]
    )
    
    # Barcha handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", show_help))
    application.add_handler(CommandHandler("cancel", cancel_conversation))
    
    application.add_handler(add_debt_conv)
    application.add_handler(search_conv)
    application.add_handler(payment_conv)
    
    # Callback query handlers - TIL O'ZGARTIRISH BU YERDA!
    application.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(show_debts_menu, pattern="^debts_list$"))
    application.add_handler(CallbackQueryHandler(show_debts, pattern=r"^debts_(active|closed|all)$"))
    application.add_handler(CallbackQueryHandler(show_debt_details, pattern=r"^details_\d+$"))
    application.add_handler(CallbackQueryHandler(close_debt, pattern=r"^close_\d+$"))
    application.add_handler(CallbackQueryHandler(confirm_delete, pattern=r"^delete_\d+$"))
    application.add_handler(CallbackQueryHandler(delete_debt, pattern=r"^(confirm|cancel)_delete_\d+$"))
    application.add_handler(CallbackQueryHandler(export_data, pattern=r"^export_(csv|excel)$"))
    
    # TIL O'ZGARTIRISH HANDLERI - ENG MUHIMI!
    application.add_handler(CallbackQueryHandler(change_language, pattern=r"^lang_(UZ|RU|EN)$"))
    
    # Matnli xabarlar handleri
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Botni ishga tushirish
    logger.info("=" * 50)
    logger.info("Bot ishga tushdi!")
    logger.info(f"Token: {TOKEN[:10]}...")
    logger.info("Tillar: UZ, RU, EN")
    logger.info("=" * 50)
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Botni ishga tushirishda xatolik: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
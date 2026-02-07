#!/usr/bin/env python
"""
Скрипт для применения миграции 0010_paymentrecord_is_recurring.py
Добавляет поле is_recurring в таблицу payment_records
"""

import os
import sys
import django

# Настройка Django окружения
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alpha.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

def apply_migration():
    """Применяет миграцию 0010"""
    try:
        print("🔄 Применение миграции 0010_paymentrecord_is_recurring...")
        
        # Проверяем, существует ли уже поле
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='payment_records' AND column_name='is_recurring'
            """)
            exists = cursor.fetchone()
            
            if exists:
                print("✅ Поле is_recurring уже существует в таблице payment_records")
                print("📝 Помечаем миграцию как выполненную...")
                call_command('migrate', 'payments', '0010', '--fake')
                print("✅ Миграция помечена как выполненная")
            else:
                print("📝 Добавляем поле is_recurring...")
                # Применяем миграцию через Django
                call_command('migrate', 'payments', '0010')
                print("✅ Миграция успешно применена!")
        
        # Проверяем результат
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name, data_type, column_default 
                FROM information_schema.columns 
                WHERE table_name='payment_records' AND column_name='is_recurring'
            """)
            result = cursor.fetchone()
            if result:
                print(f"✅ Поле успешно добавлено: {result[0]} ({result[1]}, default={result[2]})")
            else:
                print("❌ Ошибка: поле не найдено после применения миграции")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при применении миграции: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)

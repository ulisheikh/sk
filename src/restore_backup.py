"""
Backup Restore Script
User ma'lumotlarini backup fayldan qayta tiklash
"""
import json
import sqlite3
import sys
import os

def restore_user(backup_file):
    """Backup fayldan userni qayta tiklash"""
    
    if not os.path.exists(backup_file):
        print(f"❌ Xato: Fayl topilmadi: {backup_file}")
        return False
    
    # Backup faylni o'qish
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Xato: Faylni o'qib bo'lmadi: {e}")
        return False
    
    user_info = data.get('user_info', {})
    work_logs = data.get('work_logs', [])
    
    if not user_info:
        print("❌ Xato: User ma'lumotlari topilmadi")
        return False
    
    # Database ga yozish
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # User mavjudligini tekshirish
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_info['user_id'],))
        exists = cursor.fetchone()
        
        if exists:
            print(f"⚠️  Ogohlantirish: User {user_info['user_id']} allaqachon mavjud!")
            response = input("Qayta yozishni xohlaysizmi? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Bekor qilindi")
                conn.close()
                return False
            
            # Eski ma'lumotlarni o'chirish
            cursor.execute("DELETE FROM work_logs WHERE user_id = ?", (user_info['user_id'],))
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_info['user_id'],))
        
        # User insert
        cursor.execute("""
            INSERT INTO users (user_id, name, full_name, username, hourly_rate, tax_rate, work_days, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_info.get('user_id'),
            user_info.get('name', 'User'),
            user_info.get('full_name', ''),
            user_info.get('username', ''),
            user_info.get('hourly_rate', 12500),
            user_info.get('tax_rate', 3.3),
            user_info.get('work_days', '월,화,수,목,금,토,일'),
            user_info.get('is_active', 1),
            user_info.get('created_at')
        ))
        
        # Work logs insert
        for log in work_logs:
            cursor.execute("""
                INSERT INTO work_logs (user_id, work_date, hours, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                log.get('user_id'),
                log.get('work_date'),
                log.get('hours'),
                log.get('created_at')
            ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Muvaffaqiyatli tiklandi!")
        print(f"   User ID: {user_info['user_id']}")
        print(f"   Ism: {user_info.get('full_name') or user_info.get('username') or 'User'}")
        print(f"   Work logs: {len(work_logs)} ta")
        return True
        
    except Exception as e:
        print(f"❌ Xato: {e}")
        return False

def list_backups():
    """Barcha backup fayllarni ko'rsatish"""
    backup_dir = "backups"
    
    if not os.path.exists(backup_dir):
        print("📂 Backup papkasi mavjud emas")
        return []
    
    files = [f for f in os.listdir(backup_dir) if f.endswith('.json')]
    
    if not files:
        print("📂 Backup fayllar topilmadi")
        return []
    
    print(f"\n📂 Backup Fayllar ({len(files)} ta):\n")
    
    for i, file in enumerate(files, 1):
        filepath = os.path.join(backup_dir, file)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_info = data.get('user_info', {})
                user_id = user_info.get('user_id', 'Unknown')
                full_name = user_info.get('full_name') or user_info.get('username') or 'Unknown'
                deleted_at = data.get('deleted_at', 'Unknown')
                
                print(f"{i}. {file}")
                print(f"   User ID: {user_id}")
                print(f"   Ism: {full_name}")
                print(f"   O'chirilgan: {deleted_at}")
                print()
        except:
            print(f"{i}. {file} (o'qib bo'lmadi)")
    
    return files

if __name__ == "__main__":
    print("=" * 50)
    print("🔄 BACKUP RESTORE SCRIPT")
    print("=" * 50)
    print()
    
    if len(sys.argv) > 1:
        # Fayl argument sifatida berilgan
        backup_file = sys.argv[1]
        restore_user(backup_file)
    else:
        # Interaktiv rejim
        backups = list_backups()
        
        if not backups:
            print("\n❌ Backup fayllar yo'q!")
            sys.exit(1)
        
        print("Qaysi faylni tiklash kerak?")
        choice = input("Raqamini kiriting (yoki 'q' - chiqish): ")
        
        if choice.lower() == 'q':
            print("Chiqildi")
            sys.exit(0)
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                backup_file = os.path.join("backups", backups[index])
                restore_user(backup_file)
            else:
                print("❌ Noto'g'ri raqam!")
        except ValueError:
            print("❌ Noto'g'ri kirish!")
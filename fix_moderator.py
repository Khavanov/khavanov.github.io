import sqlite3
import bcrypt

def fix_moderator():
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    
    # Проверяем, есть ли пользователь
    email = 'finanalys@freshmoney.ru'
    c.execute('SELECT id, email, user_type FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    
    if user:
        print(f"Пользователь {email} существует, ID: {user[0]}, Тип: {user[2]}")
        # Обновляем пароль и тип
        hashed_password = bcrypt.hashpw('123'.encode('utf-8'), bcrypt.gensalt())
        c.execute('UPDATE users SET password = ?, user_type = ? WHERE email = ?',
                  (hashed_password, 'moderator', email))
        print(f"Пароль сброшен, тип установлен: moderator")
    else:
        # Создаём нового пользователя
        hashed_password = bcrypt.hashpw('123'.encode('utf-8'), bcrypt.gensalt())
        c.execute('INSERT INTO users (email, password, user_type) VALUES (?, ?, ?)',
                  (email, hashed_password, 'moderator'))
        print(f"Создан пользователь {email}, тип: moderator")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    fix_moderator()
import sqlite3
import bcrypt
from datetime import datetime

conn = sqlite3.connect('p2p_lending.db')
c = conn.cursor()

# Очистка базы для тестов (удалите, если хотите сохранить данные)
c.execute('DELETE FROM investments')
c.execute('DELETE FROM investment_offers')
c.execute('DELETE FROM loans')
c.execute('DELETE FROM settings')
c.execute('DELETE FROM users')

# Инвестор
hashed_password = bcrypt.hashpw('123'.encode('utf-8'), bcrypt.gensalt())
c.execute('INSERT OR IGNORE INTO users (email, password, user_type) VALUES (?, ?, ?)',
          ('investor@example.com', hashed_password, 'investor'))
investor_id = c.execute('SELECT id FROM users WHERE email = ?', ('investor@example.com',)).fetchone()[0]
c.execute('INSERT OR IGNORE INTO settings (user_id, currency, theme) VALUES (?, ?, ?)',
          (investor_id, 'RUB', 'light'))

# Заемщик
c.execute('INSERT OR IGNORE INTO users (email, password, user_type) VALUES (?, ?, ?)',
          ('borrower@example.com', hashed_password, 'borrower'))
borrower_id = c.execute('SELECT id FROM users WHERE email = ?', ('borrower@example.com',)).fetchone()[0]

# Модератор
c.execute('INSERT OR IGNORE INTO users (email, password, user_type) VALUES (?, ?, ?)',
          ('finanalys@freshmoney.ru', hashed_password, 'moderator'))

# Займ
c.execute('INSERT INTO loans (user_id, amount, term, company_name, description, file_path, status, issue_date, maturity_date, collateral) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
          (borrower_id, 10.0, 12, 'Test Company', 'Test description', 'uploads/test.pdf', 'accepted',
           '2025-04-01', '2026-04-01', 'Недвижимость'))
loan_id = c.lastrowid

# Инвестиционное предложение
c.execute('INSERT INTO investment_offers (loan_id, amount, term, interest_rate) VALUES (?, ?, ?, ?)',
          (loan_id, 10.0, 12, 5.0))

# Инвестиция
c.execute('INSERT INTO investments (investor_id, loan_id, amount, investment_date) VALUES (?, ?, ?, ?)',
          (investor_id, loan_id, 5.0, '2025-04-15'))

conn.commit()
conn.close()
import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 email TEXT UNIQUE NOT NULL,
                 password BLOB NOT NULL,
                 user_type TEXT NOT NULL
                 )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS loans (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 amount REAL NOT NULL,
                 term INTEGER NOT NULL,
                 company_name TEXT NOT NULL,
                 description TEXT NOT NULL,
                 file_path TEXT,
                 status TEXT DEFAULT 'pending',
                 FOREIGN KEY (user_id) REFERENCES users(id)
                 )''')
    
    try:
        c.execute('ALTER TABLE loans ADD COLUMN issue_date TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE loans ADD COLUMN maturity_date TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE loans ADD COLUMN collateral TEXT')
    except sqlite3.OperationalError:
        pass
    
    c.execute('''CREATE TABLE IF NOT EXISTS investment_offers (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 loan_id INTEGER,
                 amount REAL NOT NULL,
                 term INTEGER NOT NULL,
                 interest_rate REAL NOT NULL,
                 FOREIGN KEY (loan_id) REFERENCES loans(id)
                 )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS investments (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 investor_id INTEGER,
                 loan_id INTEGER,
                 amount REAL NOT NULL,
                 investment_date TEXT NOT NULL,
                 FOREIGN KEY (investor_id) REFERENCES users(id),
                 FOREIGN KEY (loan_id) REFERENCES loans(id)
                 )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                 user_id INTEGER PRIMARY KEY,
                 currency TEXT DEFAULT 'RUB',
                 theme TEXT DEFAULT 'light',
                 FOREIGN KEY (user_id) REFERENCES users(id)
                 )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS nominal_accounts (
                 user_id INTEGER PRIMARY KEY,
                 balance REAL DEFAULT 0.0,
                 FOREIGN KEY (user_id) REFERENCES users(id)
                 )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 amount REAL NOT NULL,
                 type TEXT NOT NULL,
                 method TEXT NOT NULL,
                 date TEXT NOT NULL,
                 FOREIGN KEY (user_id) REFERENCES users(id)
                 )''')
    
    conn.commit()
    conn.close()

def add_user(email, password, user_type):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('INSERT INTO users (email, password, user_type) VALUES (?, ?, ?)',
              (email, password, user_type))
    user_id = c.lastrowid
    if user_type in ('investor', 'borrower'):
        c.execute('INSERT INTO settings (user_id, currency, theme) VALUES (?, ?, ?)',
                  (user_id, 'RUB', 'light'))
        c.execute('INSERT INTO nominal_accounts (user_id, balance) VALUES (?, ?)',
                  (user_id, 0.0))
        print(f"Created nominal account for user_id={user_id}, balance=0.0")
    conn.commit()
    conn.close()
    return user_id

def get_user_by_email(email):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('SELECT id, email, password, user_type FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    conn.close()
    if user:
        return {'id': user[0], 'email': user[1], 'password': user[2], 'user_type': user[3]}
    return None

def add_loan(user_id, amount, term, company_name, description, file_path):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('INSERT INTO loans (user_id, amount, term, company_name, description, file_path, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
              (user_id, amount, term, company_name, description, file_path, 'pending'))
    conn.commit()
    conn.close()

def get_all_loans():
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('SELECT id, user_id, amount, term, company_name, description, file_path, status FROM loans WHERE status IN ("accepted", "issued")')
    loans = c.fetchall()
    conn.close()
    result = []
    for loan in loans:
        invested = get_invested_amount(loan[0])
        result.append({
            'id': loan[0], 'user_id': loan[1], 'amount': loan[2], 'term': loan[3],
            'company_name': loan[4], 'description': loan[5], 'file_path': loan[6], 
            'status': loan[7], 'invested_amount': invested
        })
    print("Loans fetched:", result)
    return result

def get_all_loans_moderator():
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('SELECT id, user_id, amount, term, company_name, description, file_path, status FROM loans')
    loans = c.fetchall()
    conn.close()
    result = []
    for loan in loans:
        invested = get_invested_amount(loan[0])
        result.append({
            'id': loan[0], 'user_id': loan[1], 'amount': loan[2], 'term': loan[3],
            'company_name': loan[4], 'description': loan[5], 'file_path': loan[6], 
            'status': loan[7], 'invested_amount': invested
        })
    return result

def get_user_loans(user_id):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('SELECT id, user_id, amount, term, company_name, description, file_path, status FROM loans WHERE user_id = ?', (user_id,))
    loans = c.fetchall()
    conn.close()
    result = []
    for loan in loans:
        invested = get_invested_amount(loan[0])
        result.append({
            'id': loan[0], 'user_id': loan[1], 'amount': loan[2], 'term': loan[3],
            'company_name': loan[4], 'description': loan[5], 'file_path': loan[6], 
            'status': loan[7], 'invested_amount': invested
        })
    return result

def get_company_details(company_id):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('SELECT id, amount, term, company_name, description, file_path, status FROM loans WHERE id = ?', (company_id,))
    company = c.fetchone()
    conn.close()
    if company:
        invested = get_invested_amount(company[0])
        return {
            'id': company[0], 'amount': company[1], 'term': company[2],
            'company_name': company[3], 'description': company[4], 'file_path': company[5],
            'status': company[6], 'invested_amount': invested
        }
    return None

def delete_loan(loan_id):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('DELETE FROM loans WHERE id = ?', (loan_id,))
    conn.commit()
    conn.close()

def add_investment_offer(loan_id, amount, term, interest_rate):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('INSERT INTO investment_offers (loan_id, amount, term, interest_rate) VALUES (?, ?, ?, ?)',
              (loan_id, amount, term, interest_rate))
    issue_date = datetime.now().strftime('%Y-%m-%d')
    maturity_date = (datetime.now().replace(year=datetime.now().year + term//12)).strftime('%Y-%m-%d')
    c.execute('UPDATE loans SET issue_date = ?, maturity_date = ?, collateral = ? WHERE id = ?',
              (issue_date, maturity_date, 'Недвижимость', loan_id))
    conn.commit()
    conn.close()

def get_investment_offer(loan_id):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('''SELECT io.loan_id, io.amount, io.term, io.interest_rate, l.user_id, l.company_name
                 FROM investment_offers io
                 JOIN loans l ON io.loan_id = l.id
                 WHERE io.loan_id = ?''', (loan_id,))
    offer = c.fetchone()
    conn.close()
    if offer:
        return {'loan_id': offer[0], 'amount': offer[1], 'term': offer[2], 'interest_rate': offer[3],
                'user_id': offer[4], 'company_name': offer[5]}
    return None

def update_loan_status(loan_id, status):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('UPDATE loans SET status = ? WHERE id = ?', (status, loan_id))
    conn.commit()
    conn.close()

def get_invested_amount(loan_id):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('SELECT SUM(amount) FROM investments WHERE loan_id = ?', (loan_id,))
    total = c.fetchone()[0]
    conn.close()
    return total or 0.0

def add_investment(investor_id, loan_id, amount):
    conn = sqlite3.connect('p2p_lending.db', isolation_level=None)
    c = conn.cursor()
    try:
        c.execute('BEGIN EXCLUSIVE')
        print(f"Attempting investment: investor_id={investor_id}, loan_id={loan_id}, amount={amount}")
        c.execute('SELECT amount, status FROM loans WHERE id = ?', (loan_id,))
        loan = c.fetchone()
        if not loan:
            print(f"Error: Loan {loan_id} not found")
            raise ValueError("Займ не найден")
        loan_amount, status = loan
        print(f"Loan details: amount={loan_amount}, status={status}")
        if status == 'issued':
            print(f"Error: Loan {loan_id} is already issued")
            raise ValueError("Займ уже выдан")
        if amount <= 0:
            print(f"Error: Invalid investment amount={amount}")
            raise ValueError("Сумма инвестиции должна быть больше 0")
        invested = get_invested_amount(loan_id)
        print(f"Current invested amount: {invested}")
        if invested + amount > loan_amount:
            print(f"Error: Investment exceeds loan: invested={invested}, amount={amount}, loan_amount={loan_amount}")
            raise ValueError("Сумма инвестиции превышает остаток по займу")
        c.execute('INSERT INTO investments (investor_id, loan_id, amount, investment_date) VALUES (?, ?, ?, ?)',
                  (investor_id, loan_id, amount, datetime.now().strftime('%Y-%m-%d')))
        new_invested = invested + amount
        print(f"New invested amount: {new_invested}")
        if abs(new_invested - loan_amount) < 0.0001:
            print(f"Loan {loan_id} fully funded, setting status to 'issued'")
            c.execute('UPDATE loans SET status = ? WHERE id = ?', ('issued', loan_id))
            transfer_to_borrower(loan_id)
        c.execute('COMMIT')
        print(f"Investment successful: {amount} for loan_id={loan_id}")
        return True
    except Exception as e:
        print(f"Investment error: {e}")
        c.execute('ROLLBACK')
        return False
    finally:
        conn.close()

def transfer_to_borrower(loan_id):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('SELECT user_id, amount FROM loans WHERE id = ?', (loan_id,))
    loan = c.fetchone()
    if not loan:
        conn.close()
        return
    borrower_id, loan_amount = loan
    c.execute('SELECT balance FROM nominal_accounts WHERE user_id = ?', (borrower_id,))
    borrower_account = c.fetchone()
    if not borrower_account:
        c.execute('INSERT INTO nominal_accounts (user_id, balance) VALUES (?, ?)', (borrower_id, 0.0))
    c.execute('UPDATE nominal_accounts SET balance = balance + ? WHERE user_id = ?', (loan_amount, borrower_id))
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT INTO transactions (user_id, amount, type, method, date) VALUES (?, ?, ?, ?, ?)',
              (borrower_id, loan_amount, 'loan_received', 'platform', date))
    print(f"Transferred {loan_amount} to borrower_id={borrower_id}")
    conn.commit()
    conn.close()

def get_investor_portfolio(investor_id):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('''SELECT l.company_name, i.amount, COALESCE(l.issue_date, 'Не указано'), 
                 COALESCE(l.maturity_date, 'Не указано'), io.interest_rate, COALESCE(l.collateral, 'Отсутствует'),
                 l.status
                 FROM investments i
                 JOIN loans l ON i.loan_id = l.id
                 JOIN investment_offers io ON l.id = io.loan_id
                 WHERE i.investor_id = ? AND l.status IN ("accepted", "issued")''', (investor_id,))
    investments = c.fetchall()
    conn.close()
    return [{'company_name': inv[0], 'amount': inv[1], 'issue_date': inv[2], 
             'maturity_date': inv[3], 'interest_rate': inv[4], 'collateral': inv[5],
             'status': inv[6]} for inv in investments]

def get_investor_summary(investor_id):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('SELECT SUM(amount) FROM investments WHERE investor_id = ?', (investor_id,))
    total_invested = c.fetchone()[0] or 0
    c.execute('SELECT COUNT(DISTINCT loan_id) FROM investments WHERE investor_id = ?', (investor_id,))
    loan_count = c.fetchone()[0] or 0
    conn.close()
    return {'total_invested': total_invested, 'loan_count': loan_count}

def get_user_settings(user_id):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('SELECT currency, theme FROM settings WHERE user_id = ?', (user_id,))
    settings = c.fetchone()
    conn.close()
    if settings:
        return {'currency': settings[0], 'theme': settings[1]}
    return {'currency': 'RUB', 'theme': 'light'}

def update_user_settings(user_id, currency, theme):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (user_id, currency, theme) VALUES (?, ?, ?)',
              (user_id, currency, theme))
    conn.commit()
    conn.close()

def get_nominal_balance(user_id):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('SELECT balance FROM nominal_accounts WHERE user_id = ?', (user_id,))
    balance = c.fetchone()
    conn.close()
    return balance[0] if balance else 0.0

def add_transaction(user_id, amount, trans_type, method):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    print(f"Transaction: user_id={user_id}, amount={amount}, type={trans_type}, method={method}")
    c.execute('SELECT balance FROM nominal_accounts WHERE user_id = ?', (user_id,))
    balance = c.fetchone()
    if not balance:
        print(f"No nominal account for user_id={user_id}, creating one")
        c.execute('INSERT INTO nominal_accounts (user_id, balance) VALUES (?, ?)', (user_id, 0.0))
        balance = (0.0,)
    print(f"Current balance: {balance[0]}")
    
    if trans_type in ('withdrawal', 'investment'):
        if balance[0] < amount:
            print(f"Insufficient funds: balance={balance[0]}, attempted={amount}")
            conn.close()
            return False
    
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT INTO transactions (user_id, amount, type, method, date) VALUES (?, ?, ?, ?, ?)',
              (user_id, amount, trans_type, method, date))
    
    if trans_type == 'deposit':
        c.execute('UPDATE nominal_accounts SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    elif trans_type in ('withdrawal', 'investment'):
        c.execute('UPDATE nominal_accounts SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
    
    c.execute('SELECT balance FROM nominal_accounts WHERE user_id = ?', (user_id,))
    new_balance = c.fetchone()
    print(f"New balance after {trans_type}: {new_balance[0] if new_balance else 0}")
    
    conn.commit()
    conn.close()
    return True

def get_transactions(user_id):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('SELECT amount, type, method, date FROM transactions WHERE user_id = ? ORDER BY date DESC', (user_id,))
    transactions = c.fetchall()
    conn.close()
    return [{'amount': t[0], 'type': t[1], 'method': t[2], 'date': t[3]} for t in transactions]
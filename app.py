from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from database import init_db, get_all_loans, get_company_details, add_loan, add_user, get_user_by_email, get_all_loans_moderator, delete_loan, add_investment_offer, get_investment_offer, update_loan_status, get_user_loans, add_investment, get_investor_portfolio, get_investor_summary, get_user_settings, update_user_settings, get_nominal_balance, add_transaction, get_transactions
import bcrypt
import sqlite3
import os
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'Uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = 'your_email@gmail.com'
SMTP_PASSWORD = 'your_app_password'
FROM_EMAIL = 'your_email@gmail.com'
TO_EMAIL = 'finanalys@freshmoney.ru'

if not os.path.exists(UPLOAD_FOLDER):
    try:
        os.makedirs(UPLOAD_FOLDER)
        print(f"Создана папка: {UPLOAD_FOLDER}")
    except Exception as e:
        print(f"Ошибка создания папки Uploads: {e}")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, email, user_type):
        self.id = id
        self.email = email
        self.user_type = user_type

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('p2p_lending.db')
    c = conn.cursor()
    c.execute('SELECT id, email, user_type FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1], user[2])
    return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_loan_email(loan_data, file_path):
    msg = MIMEMultipart()
    msg['From'] = FROM_EMAIL
    msg['To'] = TO_EMAIL
    msg['Subject'] = 'Новая заявка на ссуду'

    body = f"""
    Новая заявка на ссуду:
    Компания: {loan_data['company_name']}
    Сумма: {loan_data['amount']} млн
    Срок: {loan_data['term']} месяцев
    Описание: {loan_data['description']}
    Пользователь: {loan_data['user_email']}
    """
    msg.attach(MIMEText(body, 'plain'))

    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={os.path.basename(file_path)}'
            )
            msg.attach(part)
        except Exception as e:
            print(f"Ошибка прикрепления файла: {e}")
            flash('Заявка подана, но файл не прикреплен к письму.', 'warning')

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Письмо отправлено")
        flash('Заявка подана, и письмо отправлено.', 'success')
        return True
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        flash('Заявка подана, но письмо не отправлено.', 'error')
        return False

init_db()

@app.route('/')
def index():
    return render_template('base.html')

@app.route('/investor/home')
@login_required
def investor_home():
    if current_user.user_type != 'investor':
        flash('Доступ только для инвесторов.', 'error')
        return redirect(url_for('index'))
    summary = get_investor_summary(current_user.id)
    balance = get_nominal_balance(current_user.id)
    transactions = get_transactions(current_user.id)
    return render_template('investor.html', active_tab='home', summary=summary, balance=balance, transactions=transactions)

@app.route('/investor/market')
@login_required
def investor_market():
    if current_user.user_type != 'investor':
        flash('Доступ только для инвесторов.', 'error')
        return redirect(url_for('index'))
    loans = get_all_loans()
    return render_template('investor.html', active_tab='market', loans=loans)

@app.route('/investor/portfolio')
@login_required
def investor_portfolio():
    if current_user.user_type != 'investor':
        flash('Доступ только для инвесторов.', 'error')
        return redirect(url_for('index'))
    portfolio = get_investor_portfolio(current_user.id)
    return render_template('investor.html', active_tab='portfolio', portfolio=portfolio)

@app.route('/investor/settings', methods=['GET', 'POST'])
@login_required
def investor_settings():
    if current_user.user_type != 'investor':
        flash('Доступ только для инвесторов.', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        currency = request.form['currency']
        theme = request.form['theme']
        update_user_settings(current_user.id, currency, theme)
        flash('Настройки сохранены.', 'success')
        return redirect(url_for('investor_settings'))
    settings = get_user_settings(current_user.id)
    return render_template('investor.html', active_tab='settings', settings=settings)

@app.route('/invest/<int:loan_id>', methods=['POST'])
@login_required
def invest(loan_id):
    if current_user.user_type != 'investor':
        flash('Доступ только для инвесторов.', 'error')
        return redirect(url_for('index'))
    try:
        amount = float(request.form['amount'])
        print(f"Invest attempt: loan_id={loan_id}, amount={amount}, user_id={current_user.id}")
        if amount <= 0:
            flash('Сумма инвестиции должна быть больше 0.', 'error')
            return redirect(url_for('investor_market'))
        conn = sqlite3.connect('p2p_lending.db')
        c = conn.cursor()
        c.execute('SELECT amount, status FROM loans WHERE id = ?', (loan_id,))
        loan = c.fetchone()
        conn.close()
        if not loan:
            print(f"Invest error: Loan {loan_id} not found")
            flash('Займ не найден.', 'error')
            return redirect(url_for('investor_market'))
        loan_amount, status = loan
        print(f"Loan check: amount={loan_amount}, status={status}")
        if status == 'issued':
            print(f"Invest error: Loan {loan_id} is already issued")
            flash('Займ уже выдан.', 'error')
            return redirect(url_for('investor_market'))
        if not add_transaction(current_user.id, amount, 'investment', 'investment'):
            print(f"Invest error: Insufficient funds for user_id={current_user.id}")
            flash('Недостаточно средств для инвестиции.', 'error')
            return redirect(url_for('investor_market'))
        if add_investment(current_user.id, loan_id, amount):
            flash(f'Инвестировано {amount} млн. Остаток: {get_nominal_balance(current_user.id)} млн.', 'success')
            print(f"Invest success: {amount} for loan_id={loan_id}")
            return redirect(url_for('investor_portfolio'))
        else:
            # Откат транзакции
            print(f"Invest failed: Rolling back transaction for {amount}")
            add_transaction(current_user.id, amount, 'deposit', 'rollback')
            flash('Ошибка инвестиции: сумма превышает остаток по займу или займ уже выдан.', 'error')
            return redirect(url_for('investor_market'))
    except ValueError:
        print(f"Invest error: Invalid amount format")
        flash('Неверный формат суммы.', 'error')
        return redirect(url_for('investor_market'))

@app.route('/investor/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    if current_user.user_type != 'investor':
        flash('Доступ только для инвесторов.', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        amount = request.form['amount']
        method = request.form['method']
        print(f"Deposit attempt: amount={amount}, method={method}, user_id={current_user.id}")
        try:
            amount = float(amount)
            if amount <= 0:
                flash('Сумма пополнения должна быть больше 0.', 'error')
                return redirect(url_for('deposit'))
            if add_transaction(current_user.id, amount, 'deposit', method):
                flash(f'Счёт пополнен на {amount} млн через {method}. Новый баланс: {get_nominal_balance(current_user.id)} млн.', 'success')
            else:
                flash('Ошибка при пополнении счёта. Проверьте данные.', 'error')
            return redirect(url_for('investor_home'))
        except ValueError:
            flash('Неверный формат суммы.', 'error')
            return redirect(url_for('deposit'))
    return render_template('deposit.html')

@app.route('/investor/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    if current_user.user_type != 'investor':
        flash('Доступ только для инвесторов.', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            method = request.form['method']
            if amount <= 0:
                flash('Сумма вывода должна быть больше 0.', 'error')
                return redirect(url_for('withdraw'))
            if add_transaction(current_user.id, amount, 'withdrawal', method):
                flash(f'Выведено {amount} млн на {method}. Баланс: {get_nominal_balance(current_user.id)} млн.', 'success')
                return redirect(url_for('investor_home'))
            else:
                flash('Недостаточно средств для вывода.', 'error')
                return redirect(url_for('withdraw'))
        except ValueError:
            flash('Неверный формат суммы.', 'error')
            return redirect(url_for('withdraw'))
    return render_template('withdraw.html')

@app.route('/borrower', methods=['GET', 'POST'])
@login_required
def borrower():
    if current_user.user_type != 'borrower':
        flash('Доступ только для заёмщиков.', 'error')
        return redirect(url_for('index'))
    loans = get_user_loans(current_user.id)
    balance = get_nominal_balance(current_user.id)
    return render_template('borrower.html', loans=loans, balance=balance)

@app.route('/moderator')
@login_required
def moderator():
    if current_user.user_type != 'moderator':
        flash('Доступ только для модераторов.', 'error')
        return redirect(url_for('index'))
    loans = get_all_loans_moderator()
    return render_template('moderator.html', loans=loans)

@app.route('/submit_loan', methods=['POST'])
@login_required
def submit_loan():
    if current_user.user_type != 'borrower':
        flash('Доступ только для заемщиков.', 'error')
        return redirect(url_for('index'))
    amount = float(request.form['amount'])
    term = int(request.form['term'])
    company_name = request.form['company_name']
    description = request.form['description']
    file = request.files['file']
    
    file_path = None
    filename = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            print(f"Попытка сохранить файл: {file_path}")
            file.save(file_path)
            if os.path.exists(file_path):
                print(f"Файл успешно сохранен: {file_path}")
                add_loan(current_user.id, amount, term, company_name, description, filename)
                loan_data = {
                    'company_name': company_name,
                    'amount': amount,
                    'term': term,
                    'description': description,
                    'user_email': current_user.email
                }
                send_loan_email(loan_data, file_path)
            else:
                print(f"Файл не сохранен: {file_path}")
                flash('Ошибка: файл не был сохранен на сервере.', 'error')
                return redirect(url_for('borrower'))
        except Exception as e:
            print(f"Ошибка сохранения файла: {e}")
            flash('Ошибка при сохранении файла.', 'error')
            return redirect(url_for('borrower'))
    else:
        flash('Пожалуйста, загрузите файл в формате PDF.', 'error')
    
    return redirect(url_for('borrower'))

@app.route('/delete_loan/<int:loan_id>', methods=['POST'])
@login_required
def delete_loan_route(loan_id):
    if current_user.user_type != 'moderator':
        flash('Доступ только для модераторов.', 'error')
        return redirect(url_for('moderator'))
    delete_loan(loan_id)
    flash('Заявка удалена.', 'success')
    return redirect(url_for('moderator'))

@app.route('/create_offer/<int:loan_id>', methods=['GET', 'POST'])
@login_required
def create_offer(loan_id):
    if current_user.user_type != 'moderator':
        flash('Доступ только для модераторов.', 'error')
        return redirect(url_for('moderator'))
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            term = int(request.form['term'])
            interest_rate = float(request.form['interest_rate'])
            add_investment_offer(loan_id, amount, term, interest_rate)
            update_loan_status(loan_id, 'approved')
            flash('Инвестиционное предложение создано.', 'success')
            return redirect(url_for('moderator'))
        except ValueError:
            flash('Неверный формат данных.', 'error')
            return redirect(url_for('create_offer', loan_id=loan_id))
    return render_template('create_offer.html', loan_id=loan_id)

@app.route('/investment_offer/<int:loan_id>', methods=['GET', 'POST'])
@login_required
def investment_offer(loan_id):
    if current_user.user_type != 'borrower':
        flash('Доступ только для заемщиков.', 'error')
        return redirect(url_for('borrower'))
    offer = get_investment_offer(loan_id)
    if not offer or offer['user_id'] != current_user.id:
        flash('Предложение не найдено или недоступно.', 'error')
        return redirect(url_for('borrower'))
    
    if request.method == 'POST':
        if request.form.get('accept') == 'yes':
            update_loan_status(loan_id, 'accepted')
            flash('Предложение принято. Заявка размещена на платформе.', 'success')
        else:
            update_loan_status(loan_id, 'rejected')
            flash('Предложение отклонено.', 'error')
        return redirect(url_for('borrower'))
    
    return render_template('investment_offer.html', offer=offer)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f"Попытка скачать файл: {file_path}")
        if not os.path.exists(file_path):
            print(f"Файл не существует: {file_path}")
            flash(f'Файл {filename} не найден на сервере.', 'error')
            return redirect(request.referrer or url_for('index'))
        print(f"Отправка файла: {file_path}")
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        print(f"Ошибка при скачивании файла: {e}")
        flash('Ошибка при скачивании файла.', 'error')
        return redirect(request.referrer or url_for('index'))

@app.route('/company/<int:company_id>')
@login_required
def company(company_id):
    if current_user.user_type != 'investor':
        flash('Доступ только для инвесторов.', 'error')
        return redirect(url_for('index'))
    print(f"Запрос компании: company_id={company_id}")
    company = get_company_details(company_id)
    if company:
        return render_template('company.html', company=company)
    flash('Компания не найдена.', 'error')
    return redirect(url_for('investor_market'))

@app.route('/register/<user_type>', methods=['GET', 'POST'])
def register(user_type):
    if user_type not in ['investor', 'borrower', 'moderator']:
        flash('Неверный тип пользователя.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if get_user_by_email(email):
            flash('Пользователь с таким email уже существует.', 'error')
            return redirect(url_for('register', user_type=user_type))
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_id = add_user(email, hashed_password, user_type)
        user_obj = User(user_id, email, user_type)
        login_user(user_obj)
        flash('Регистрация успешна!', 'success')
        
        if user_type == 'investor':
            return redirect(url_for('investor_home'))
        elif user_type == 'borrower':
            return redirect(url_for('borrower'))
        elif user_type == 'moderator':
            return redirect(url_for('moderator'))
    
    return render_template('register.html', user_type=user_type)

@app.route('/login/<user_type>', methods=['GET', 'POST'])
def login(user_type):
    if user_type not in ['investor', 'borrower', 'moderator']:
        flash('Неверный тип пользователя.', 'error')
        return redirect(url_for('index'))
        
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = get_user_by_email(email)
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            user_obj = User(user['id'], user['email'], user['user_type'])
            login_user(user_obj)
            flash('Вход выполнен успешно!', 'success')
            if user['user_type'] == 'moderator':
                return redirect(url_for('moderator'))
            elif user['user_type'] == 'investor':
                return redirect(url_for('investor_home'))
            elif user['user_type'] == 'borrower':
                return redirect(url_for('borrower'))
            else:
                flash('Неверный тип пользователя.', 'error')
                return redirect(url_for('login', user_type=user_type))
        else:
            flash('Неверный email или пароль.', 'error')
    
    return render_template('login.html', user_type=user_type)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
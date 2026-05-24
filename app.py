from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from process_client import ProcessLauncher
from database import db
from datetime import datetime
import os
import json
import traceback
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from process_forms import get_form_schema
import psycopg2

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)

# Секретный ключ для сессий
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')

# Инициализация Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, авторизуйтесь для доступа к этой странице'
login_manager.login_message_category = 'warning'

# Инициализация клиента
runa_launcher = ProcessLauncher()

# Конфигурация для BPMN диаграмм
BPMN_DIAGRAMS_PATH = 'static/bpmn_diagrams'
PROCESS_BPMN_MAP = {
    'process_1': 'process_1.png',
    'process_2': 'process_2.png',
    'process_3': 'process_3.png'
}

# Создаем директорию для BPMN диаграмм
os.makedirs(BPMN_DIAGRAMS_PATH, exist_ok=True)


# Модель пользователя для Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get(user_id):
        """Получить пользователя по ID"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT id, username, email, password_hash FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                return User(
                    id=user_data['id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=user_data['password_hash']
                )
            return None
        except Exception as e:
            print(f"Ошибка при получении пользователя: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                db.return_connection(conn)

    @staticmethod
    def find_by_username(username):
        """Найти пользователя по имени"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT id, username, email, password_hash FROM users WHERE username = %s", (username,))
            user_data = cursor.fetchone()
            if user_data:
                return User(
                    id=user_data['id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=user_data['password_hash']
                )
            return None
        except Exception as e:
            print(f"Ошибка при поиске пользователя: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                db.return_connection(conn)

    @staticmethod
    def create_user(username, email, password):
        """Создать нового пользователя"""
        conn = None
        cursor = None
        try:
            password_hash = generate_password_hash(password)
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (username, email, password_hash, datetime.now()))
            user_id = cursor.fetchone()[0]
            conn.commit()
            return user_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Ошибка при создании пользователя: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                db.return_connection(conn)


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# Функция для инициализации таблицы пользователей
def init_users_table():
    """Создание таблицы пользователей и добавление тестового пользователя"""
    conn = None
    cursor = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # Создаем таблицу пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)

        # Создаем индексы
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """)

        conn.commit()
        print("Таблица users успешно создана/проверена")

        # Добавляем тестового пользователя, если его нет
        cursor.execute("SELECT id FROM users WHERE username = %s", ('user',))
        if not cursor.fetchone():
            test_password = generate_password_hash('password123')
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, created_at)
                VALUES (%s, %s, %s, %s)
            """, ('user', 'user@example.com', test_password, datetime.now()))
            conn.commit()
            print("Тестовый пользователь создан: user / password123")

    except Exception as e:
        print(f"Ошибка при инициализации таблицы users: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            db.return_connection(conn)


# Маршруты авторизации
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        if not username or not password:
            flash('Пожалуйста, заполните все поля', 'danger')
            return render_template('login.html')

        user = User.find_by_username(username)

        if user and user.check_password(password):
            login_user(user, remember=remember)

            # Обновляем время последнего входа
            conn = None
            cursor = None
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET last_login = %s WHERE id = %s", (datetime.now(), user.id))
                conn.commit()
            except Exception as e:
                print(f"Ошибка при обновлении last_login: {e}")
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    db.return_connection(conn)

            flash(f'Добро пожаловать, {user.username}!', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Простая валидация
        errors = []
        if not username or len(username) < 3:
            errors.append('Имя пользователя должно содержать минимум 3 символа')
        if not email or '@' not in email:
            errors.append('Введите корректный email адрес')
        if not password or len(password) < 4:
            errors.append('Пароль должен содержать минимум 4 символа')
        if password != confirm_password:
            errors.append('Пароли не совпадают')

        # Проверяем существование пользователя
        existing_user = User.find_by_username(username)
        if existing_user:
            errors.append('Пользователь с таким именем уже существует')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')

        # Создаем пользователя
        user_id = User.create_user(username, email, password)
        if user_id:
            flash('Регистрация успешно завершена! Теперь вы можете войти в систему.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Ошибка при регистрации. Возможно, пользователь с таким email уже существует.', 'danger')

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('login'))


# Защищенные маршруты (добавляем @login_required ко всем страницам)
@app.route('/')
@login_required
def index():
    """Главная страница"""
    processes = db.get_all_process_definitions()
    return render_template('index.html', processes=processes, user=current_user)


@app.route('/history')
@login_required
def history_page():
    """Страница истории запусков"""
    return render_template('history.html', user=current_user)


@app.route('/logs/<process_id>')
@login_required
def logs_page(process_id):
    """Страница с логами выполнения процесса"""
    bpmn_image = 'process_1.png'  # Значение по умолчанию

    # Маппинг для определения схемы по ID процесса
    def get_bpmn_image(proc_id):
        bpmn_map = {
            'process_1': 'process_1.png',
            'process_2': 'process_2.png',
            'process_3': 'process_3.png'
        }
        return bpmn_map.get(proc_id, 'process_1.png')

    # Пробуем определить по префиксу в process_id
    if 'process_2' in process_id or process_id.startswith('process_2') or process_id.startswith('2_'):
        bpmn_image = 'process_2.png'
    elif 'process_3' in process_id or process_id.startswith('process_3') or process_id.startswith('3_'):
        bpmn_image = 'process_3.png'
    elif 'process_1' in process_id or process_id.startswith('process_1') or process_id.startswith('1_'):
        bpmn_image = 'process_1.png'

    # Пытаемся получить из БД для точного определения
    conn = None
    cursor = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT proc_id FROM procHist WHERE instance_id = %s
        """, (process_id,))

        record = cursor.fetchone()
        if record and record.get('proc_id'):
            bpmn_image = get_bpmn_image(record['proc_id'])

    except Exception as e:
        print(f"Ошибка при получении BPMN схемы из БД: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            db.return_connection(conn)

    # Проверяем, существует ли файл
    bpmn_path = os.path.join(BPMN_DIAGRAMS_PATH, bpmn_image)
    if not os.path.exists(bpmn_path):
        print(f"BPMN файл не найден: {bpmn_path}")
        bpmn_image = None

    return render_template('logs.html',
                           process_id=process_id,
                           bpmn_image=bpmn_image,
                           user=current_user)


# API маршруты (добавляем @login_required)
@app.route('/api/processes', methods=['GET'])
@login_required
def get_processes():
    """Получить список доступных процессов"""
    try:
        processes = db.get_all_process_definitions()
        return jsonify({'success': True, 'processes': processes}), 200
    except Exception as e:
        print(f"Ошибка: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/processes/<proc_id>', methods=['GET'])
@login_required
def get_process(proc_id):
    """Получить информацию о процессе"""
    try:
        process = db.get_process_definition(proc_id)
        if process:
            return jsonify({'success': True, 'process': process}), 200
        else:
            return jsonify({'success': False, 'error': 'Процесс не найден'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    """Получить историю запусков"""
    conn = None
    cursor = None
    try:
        limit = request.args.get('limit', default=100, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # Получаем данные из БД
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Получаем общее количество
        cursor.execute("SELECT COUNT(*) as total FROM procHist")
        total_count = cursor.fetchone()['total']

        # Получаем записи
        cursor.execute("""
            SELECT 
                id, instance_id, proc_id, proc_name, status,
                variables, result, started_at, completed_at, 
                duration_seconds, created_by, error_message
            FROM procHist 
            ORDER BY started_at DESC 
            LIMIT %s OFFSET %s
        """, (limit, offset))

        records = cursor.fetchall()

        # Форматируем записи для фронтенда
        formatted_records = []
        for record in records:
            # Парсим variables
            variables = record.get('variables', {})
            if isinstance(variables, str):
                try:
                    variables = json.loads(variables)
                except:
                    variables = {}

            # Парсим result
            result_data = record.get('result', {})
            if isinstance(result_data, str):
                try:
                    result_data = json.loads(result_data)
                except:
                    result_data = {}

            # Форматируем дату
            started_at = record.get('started_at')
            formatted_date = "—"
            if started_at:
                try:
                    if isinstance(started_at, datetime):
                        formatted_date = started_at.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(started_at, str):
                        date_str = started_at.split('.')[0].replace('T', ' ')
                        formatted_date = date_str
                except:
                    formatted_date = "—"

            # Определяем статус для отображения
            status = record.get('status', 'UNKNOWN')
            if status == 'COMPLETED':
                status_display = 'success'
                status_text = '✓ Успешно'
            elif status == 'ERROR':
                status_display = 'error'
                status_text = '✗ Ошибка'
            elif status == 'IN_PROGRESS':
                status_display = 'in_progress'
                status_text = '⟳ В процессе'
            elif status == 'REWORK_NEEDED':
                status_display = 'rework'
                status_text = '⟳ Требуется доработка'
            else:
                status_display = 'unknown'
                status_text = status

            # Получаем данные из variables
            equipment_type = variables.get('equipment_type', '—')
            if not equipment_type or equipment_type == 'unknown':
                equipment_type = '—'

            author = variables.get('author', variables.get('created_by', record.get('created_by', '—')))
            if not author or author == 'system':
                author = '—'

            # Формируем результат для отображения
            result_summary = '—'
            if status == 'COMPLETED':
                if 'calculated_time' in result_data:
                    result_summary = f"{result_data['calculated_time']} м/ч"
                elif 'total_cost' in result_data:
                    result_summary = f"{result_data['total_cost']:,.2f} руб."
                elif 'abc_analysis' in result_data and result_data['abc_analysis']:
                    abc_class = result_data['abc_analysis'].get('class', '')
                    result_summary = f"Класс {abc_class}"
                elif 'planning_result' in result_data and result_data['planning_result']:
                    calc_time = result_data['planning_result'].get('calculated_time', 0)
                    result_summary = f"{calc_time} м/ч"

            formatted_records.append({
                'id': record['id'],
                'timestamp': formatted_date,
                'instance_id': record['instance_id'],
                'proc_id': record['proc_id'],
                'proc_name': record['proc_name'],
                'status': status_display,
                'status_text': status_text,
                'equipment_type': equipment_type,
                'author': author,
                'result_summary': result_summary,
                'duration_seconds': record.get('duration_seconds'),
                'error_message': record.get('error_message')
            })

        return jsonify({
            'success': True,
            'total': total_count,
            'records': formatted_records
        }), 200

    except Exception as e:
        print(f"Ошибка в /api/history: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'records': []
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            db.return_connection(conn)


@app.route('/api/logs/<instance_id>', methods=['GET'])
@login_required
def get_logs(instance_id):
    """Получить логи выполнения процесса"""
    conn = None
    cursor = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT 
                instance_id, proc_id, proc_name, status,
                variables, steps, logs, result,
                started_at, completed_at, duration_seconds,
                created_by, error_message
            FROM procHist 
            WHERE instance_id = %s
        """, (instance_id,))

        record = cursor.fetchone()

        if not record:
            return jsonify({
                'success': False,
                'error': 'Процесс не найден'
            }), 404

        # Парсим JSON поля
        variables = record.get('variables', {})
        if isinstance(variables, str):
            try:
                variables = json.loads(variables)
            except:
                variables = {}

        steps = record.get('steps', [])
        if isinstance(steps, str):
            try:
                steps = json.loads(steps)
            except:
                steps = []

        logs = record.get('logs', [])
        if isinstance(logs, str):
            try:
                logs = json.loads(logs)
            except:
                logs = []

        result_data = record.get('result', {})
        if isinstance(result_data, str):
            try:
                result_data = json.loads(result_data)
            except:
                result_data = {}

        # Форматируем логи для отображения
        formatted_logs = []
        icon_map = {
            'script': '⚙️',
            'user_task': '👤',
            'decision': '🤔',
            'system': '🔧',
            'init': '🚀',
            'complete': '✅',
            'error': '❌'
        }

        for log in logs:
            # Получаем временную метку
            timestamp = log.get('timestamp', '')
            timestamp_formatted = ''
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        timestamp_formatted = dt.strftime('%H:%M:%S.%f')[:-3]
                    elif isinstance(timestamp, datetime):
                        timestamp_formatted = timestamp.strftime('%H:%M:%S.%f')[:-3]
                except:
                    timestamp_formatted = str(timestamp)[:12] if len(str(timestamp)) > 12 else str(timestamp)

            step_type = log.get('type', 'system')

            formatted_logs.append({
                'timestamp_formatted': timestamp_formatted,
                'step': log.get('step', ''),
                'message': log.get('message', ''),
                'level': log.get('level', 'INFO'),
                'type': step_type,
                'icon': icon_map.get(step_type, '📌'),
                'data': log.get('data')
            })

        # Если нет логов, но есть steps - создаем из steps
        if not formatted_logs and steps:
            for step in steps:
                step_type = step.get('type', 'script')
                formatted_logs.append({
                    'timestamp_formatted': '',
                    'step': step.get('step', ''),
                    'message': f"Выполнен шаг: {step.get('step')}",
                    'level': 'INFO',
                    'type': step_type,
                    'icon': icon_map.get(step_type, '📌'),
                    'data': step.get('result')
                })

        # Форматируем даты
        started_at = record.get('started_at')
        started_at_formatted = ''
        if started_at:
            try:
                if isinstance(started_at, datetime):
                    started_at_formatted = started_at.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(started_at, str):
                    date_str = started_at.split('.')[0].replace('T', ' ')
                    started_at_formatted = date_str
            except:
                started_at_formatted = str(started_at)

        completed_at = record.get('completed_at')
        completed_at_formatted = ''
        if completed_at:
            try:
                if isinstance(completed_at, datetime):
                    completed_at_formatted = completed_at.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(completed_at, str):
                    date_str = completed_at.split('.')[0].replace('T', ' ')
                    completed_at_formatted = date_str
            except:
                completed_at_formatted = str(completed_at)

        # Статистика по логам
        error_count = len([l for l in formatted_logs if l.get('level') == 'ERROR'])
        warning_count = len([l for l in formatted_logs if l.get('level') == 'WARNING'])
        success_count = len([l for l in formatted_logs if l.get('level') == 'SUCCESS'])

        # BPMN схема
        proc_id = record.get('proc_id')
        bpmn_image = PROCESS_BPMN_MAP.get(proc_id, 'process_1.png')

        return jsonify({
            'success': True,
            'process_id': instance_id,
            'process_info': {
                'proc_id': proc_id,
                'proc_name': record.get('proc_name'),
                'status': record.get('status'),
                'started_at_formatted': started_at_formatted,
                'completed_at_formatted': completed_at_formatted,
                'duration_seconds': record.get('duration_seconds'),
                'variables': variables,
                'created_by': record.get('created_by'),
                'error_message': record.get('error_message')
            },
            'logs': formatted_logs,
            'total_logs': len(formatted_logs),
            'statistics': {
                'errors': error_count,
                'warnings': warning_count,
                'success': success_count
            },
            'result': result_data,
            'bpmn': {
                'image_url': f'/api/bpmn/{bpmn_image}',
                'definition_id': proc_id
            }
        }), 200

    except Exception as e:
        print(f"Ошибка в /api/logs: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            db.return_connection(conn)


@app.route('/api/history/<instance_id>', methods=['GET'])
@login_required
def get_history_record(instance_id):
    """Получить конкретную запись истории"""
    try:
        records = db.get_process_history(instance_id=instance_id)
        if records:
            return jsonify({'success': True, 'record': records[0]}), 200
        else:
            return jsonify({'success': False, 'error': 'Запись не найдена'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/history', methods=['DELETE'])
@login_required
def clear_history():
    """Очистить историю"""
    try:
        days = request.args.get('days', type=int)
        if days:
            deleted = db.delete_process_history(days_old=days)
            message = f'Удалено записей старше {days} дней: {deleted}'
        else:
            deleted = db.delete_process_history()
            message = f'Удалено записей: {deleted}'

        return jsonify({'success': True, 'message': message, 'deleted': deleted}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/statistics', methods=['GET'])
@login_required
def get_statistics():
    """Получить статистику по процессам"""
    try:
        stats = db.get_process_statistics()
        return jsonify({'success': True, 'statistics': stats}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bpmn/<filename>')
@login_required
def get_bpmn_diagram(filename):
    """Получить BPMN диаграмму"""
    try:
        return send_from_directory(BPMN_DIAGRAMS_PATH, filename)
    except Exception as e:
        return jsonify({'error': 'BPMN диаграмма не найдена'}), 404


@app.route('/api/check', methods=['GET'])
def check_api():
    """Проверка API (публичный)"""
    return jsonify({
        'success': True,
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/api/processes/<proc_id>/form_schema', methods=['GET'])
@login_required
def get_process_form_schema(proc_id):
    """Вернуть схему формы для ввода переменных процесса"""
    schema = get_form_schema(proc_id)
    if schema:
        return jsonify({'success': True, 'schema': schema}), 200
    else:
        return jsonify({'success': False, 'error': 'Схема не найдена'}), 404


@app.route('/start_process', methods=['POST'])
@login_required
def start_process():
    """Запуск процесса"""
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "No JSON data provided"}), 400

    definition_id = data.get('definition_id')
    variables = data.get('variables', {})
    created_by = current_user.username  # Используем имя текущего пользователя

    if not definition_id:
        return jsonify({"success": False, "error": "definition_id is required"}), 400

    # Проверяем существование процесса
    process_def = db.get_process_definition(definition_id)
    if not process_def:
        return jsonify({"success": False, "error": f"Процесс {definition_id} не найден"}), 404

    try:
        # Запускаем процесс
        result = runa_launcher.start_process(definition_id, variables)
        process_id = result.get('process_instance_id')

        # Получаем логи и шаги из launcher
        logs = runa_launcher.get_process_logs(process_id)
        steps = runa_launcher.get_process_steps(process_id) if hasattr(runa_launcher, 'get_process_steps') else []

        # Сохраняем в БД
        db.save_process_history(
            instance_id=process_id,
            proc_id=definition_id,
            proc_name=process_def['name'],
            variables=variables,
            steps=steps,
            logs=logs,
            result=result.get('result'),
            status='COMPLETED' if result.get('status') == 'success' else 'ERROR',
            error=None if result.get('status') == 'success' else result.get('message'),
            created_by=created_by
        )

        return jsonify({
            "success": True,
            "status": "success",
            "process_instance_id": process_id,
            "message": result.get('message', 'Процесс успешно запущен'),
            "result": result.get('result')
        }), 200

    except Exception as e:
        error_msg = str(e)
        traceback.print_exc()
        return jsonify({"success": False, "error": error_msg}), 500


@app.route('/process_status/<process_id>', methods=['GET'])
@login_required
def process_status(process_id):
    """Получение статуса процесса"""
    status = runa_launcher.get_process_status(process_id)
    if status:
        return jsonify({'success': True, 'status': status}), 200
    else:
        return jsonify({"success": False, "error": "Процесс не найден"}), 404


@app.route('/health', methods=['GET'])
def health():
    """Проверка здоровья приложения (публичный)"""
    return jsonify({
        "status": "ok",
        "database": "connected",
        "timestamp": datetime.now().isoformat()
    }), 200


if __name__ == '__main__':
    # Инициализируем таблицу пользователей при запуске
    init_users_table()

    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    app.run(host=host, port=port, debug=debug)
🛠 Инструкция по настройке проекта
📋 Содержание
Локальная разработка
Настройка email
Миграция из Telegram бота
Деплой на Render.com
Настройка расписания
Troubleshooting
---
🖥 Локальная разработка
Шаг 1: Установка зависимостей
```bash
# Клонировать репозиторий
git clone https://github.com/YOUR_USERNAME/badminton-club-django.git
cd badminton-club-django

# Создать виртуальное окружение
python -m venv venv

# Активировать (Linux/Mac)
source venv/bin/activate

# Активировать (Windows)
venv\Scripts\activate

# Обновить pip
pip install --upgrade pip

# Установить зависимости для разработки
pip install -r requirements/dev.txt
```
Шаг 2: Настроить переменные окружения
```bash
# Скопировать пример
cp .env.example .env

# Отредактировать .env
nano .env  # или любой текстовый редактор
```
Минимальные настройки для локальной разработки:
```bash
SECRET_KEY=dev-secret-key-change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/badminton
DJANGO_SETTINGS_MODULE=config.settings.dev
```
Шаг 3: Запустить PostgreSQL
```bash
# Запустить Docker контейнер
docker-compose up -d

# Проверить что БД работает
docker-compose ps

# Посмотреть логи (если проблемы)
docker-compose logs db
```
Шаг 4: Применить миграции
```bash
cd backend

# Создать миграции
python manage.py makemigrations

# Применить миграции
python manage.py migrate

# Создать суперпользователя
python manage.py createsuperuser
# Email: admin@example.com
# Password: (введи свой пароль)
```
Шаг 5: Загрузить начальные данные (опционально)
```bash
# Если есть fixtures
python manage.py loaddata initial_data.json
```
Шаг 6: Запустить сервер
```bash
# Запустить Django сервер
python manage.py runserver

# Открой браузер:
# http://localhost:8000 - главная страница
# http://localhost:8000/admin - админка
```
---
📧 Настройка Email
Gmail SMTP (бесплатно)
Шаг 1: Включить 2FA в Google аккаунте
Зайди в https://myaccount.google.com/security
Включи "2-Step Verification"
Шаг 2: Создать App Password
Зайди в https://myaccount.google.com/apppasswords
Выбери "Mail" и "Other (Custom name)"
Введи название: "Badminton Django"
Скопируй сгенерированный пароль (16 символов)
Шаг 3: Добавить в .env
```bash
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=abcd efgh ijkl mnop  # App Password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```
Шаг 4: Проверить отправку
```bash
python manage.py shell
```
```python
from django.core.mail import send_mail

send_mail(
    'Test Email',
    'This is a test message.',
    'your-email@gmail.com',
    ['recipient@example.com'],
    fail_silently=False,
)
# Если вернёт 1 - успешно!
```
---
🚀 Миграция из Telegram бота
Шаг 1: Экспорт пользователей из бота
```python
# В старом боте (bot/config.py)
from config import KNOWN_USERS
import json

users_export = []
for telegram_id, display_name in KNOWN_USERS.items():
    users_export.append({
        'telegram_id': telegram_id,
        'display_name': display_name,
    })

with open('users_export.json', 'w', encoding='utf-8') as f:
    json.dump(users_export, f, ensure_ascii=False, indent=2)
```
Шаг 2: Импорт в Django
```bash
# Скопируй users_export.json в backend/

cd backend
python manage.py shell
```
```python
import json
from apps.accounts.models import User

# Загрузить данные
with open('users_export.json', 'r', encoding='utf-8') as f:
    users_data = json.load(f)

# Импортировать
for user_data in users_data:
    User.objects.get_or_create(
        telegram_id=user_data['telegram_id'],
        defaults={
            'display_name': user_data['display_name'],
            'approval_status': 'approved',  # автоматически одобрены
            'is_active': True,
            'email': f"user_{user_data['telegram_id']}@temp.local",  # временный
        }
    )

print(f"Импортировано пользователей: {User.objects.count()}")
```
Шаг 3: Отправить приглашения
```bash
python manage.py send_invitations
```
Или вручную через shell:
```python
from apps.accounts.models import User
from django.core.mail import send_mail

for user in User.objects.filter(approval_status='approved'):
    # Генерируем временный пароль
    temp_password = User.objects.make_random_password(length=10)
    user.set_password(temp_password)
    user.save()
    
    # Отправляем приглашение
    send_mail(
        subject='Новая система записи на бадминтон',
        message=f'''Привет, {user.display_name}!

Мы перешли с Telegram бота на новый сайт.

Сайт: https://your-site.onrender.com
Логин: {user.email}
Временный пароль: {temp_password}

Пожалуйста, войди и измени пароль.
''',
        from_email='your-email@gmail.com',
        recipient_list=[user.email],
    )
```
---
🌐 Деплой на Render.com
Шаг 1: Создать аккаунт
Зайди на https://render.com
Sign Up → подключи GitHub
Шаг 2: Подключить репозиторий
Dashboard → New → Blueprint
Выбери репозиторий `badminton-club-django`
Render найдёт `render.yaml` автоматически
Нажми "Apply"
Шаг 3: Настроить переменные окружения
После создания сервиса:
Зайди в badminton-web → Environment
Добавь:
```
   ALLOWED_HOSTS = badminton-web.onrender.com
   EMAIL_HOST_USER = your-email@gmail.com
   EMAIL_HOST_PASSWORD = your-app-password
   ```
Шаг 4: Создать суперпользователя
Зайди в badminton-web → Shell
Выполни:
```bash
   cd backend
   python manage.py createsuperuser
   ```
Шаг 5: Проверить
Открой: `https://badminton-web.onrender.com`
⚠️ Важно: Первый запрос после sleep может занять 30-60 секунд (бесплатный план).
---
⏰ Настройка расписания
Django-cron (используется в проекте)
Расписание задач:
Понедельник 00:01 - Открытие записи
Вторник 09:45 - Напоминание неответившим
Среда 17:00 - Закрытие записи
Каждые 5 минут - Автопродвижение из резерва
Проверить задачи:
```bash
python manage.py cron_info
```
Запустить вручную:
```bash
python manage.py runcrons
```
Render.com cron service запускает это автоматически каждую минуту.
---
🐛 Troubleshooting
БД не запускается (Docker)
```bash
# Остановить и удалить контейнеры
docker-compose down -v

# Запустить заново
docker-compose up -d

# Проверить статус
docker-compose ps
```
Email не отправляются
Проверь:
✅ App Password создан (не обычный пароль Google!)
✅ EMAIL_HOST_USER и EMAIL_HOST_PASSWORD в .env
✅ 2FA включена в Google аккаунте
Тест:
```bash
python manage.py shell
```
```python
from django.core.mail import send_mail
send_mail('Test', 'Body', 'from@gmail.com', ['to@email.com'])
```
Миграции не применяются
```bash
# Показать список миграций
python manage.py showmigrations

# Откатить миграции
python manage.py migrate app_name zero

# Применить заново
python manage.py migrate
```
Static files не загружаются (production)
```bash
# Собрать статику
python manage.py collectstatic --no-input

# Проверить настройки в prod.py
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```
Render.com: 502 Bad Gateway
Причины:
Build failed - проверь логи в Dashboard
ALLOWED_HOSTS неправильный - добавь домен Render
DATABASE_URL неправильный - проверь подключение к БД
Логи:
```
Dashboard → badminton-web → Logs
```
---
📝 Полезные команды
```bash
# Django
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py shell
python manage.py dbshell

# Тесты
pytest
pytest --cov
pytest -v

# Форматирование
black backend/
isort backend/

# Docker
docker-compose up -d
docker-compose down
docker-compose logs -f
docker-compose exec db psql -U postgres -d badminton
```
---
🆘 Нужна помощь?
Проверь 00-project_context.md
Проверь engineering_rules.md
Создай Issue на GitHub
Посмотри логи: `docker-compose logs` или Render Dashboard
---
Удачи! 🎾

🏸 Backend - Django Application
📋 Текущий статус
✅ Создана базовая структура:
`manage.py` - Django команды
`config/` - настройки проекта (base/dev/prod)
`config/urls.py` - URL роутинг
`config/wsgi.py` - WSGI для production
`apps/accounts/` - приложение пользователей (модель User)
⚠️ Требуется доработка:
Модели для `games/` и `registrations/`
Views и templates
Services (rebuild_queue, register_user)
Django admin настройки
Cron jobs для расписания
---
🚀 Быстрый старт
1. Установить зависимости
```bash
# Из корня проекта
pip install -r requirements/dev.txt
```
2. Настроить .env
```bash
# Скопировать пример
cp .env.example .env

# Отредактировать .env
# Минимум нужно:
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/badminton
```
3. Запустить PostgreSQL
```bash
# Из корня проекта
docker-compose up -d
```
4. Применить миграции
```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```
5. Создать суперпользователя
```bash
python manage.py createsuperuser
```
6. Запустить сервер
```bash
python manage.py runserver
```
Откроется: http://localhost:8000
---
📁 Структура
```
backend/
├── manage.py                     # Django CLI
├── config/                       # Настройки проекта
│   ├── settings/
│   │   ├── base.py              # ✅ Базовые настройки
│   │   ├── dev.py               # ✅ Development
│   │   └── prod.py              # ✅ Production
│   ├── urls.py                  # ✅ URL роутинг
│   └── wsgi.py                  # ✅ WSGI
└── apps/                        # Django приложения
    ├── accounts/                # ✅ Пользователи
    │   └── models.py            # ✅ User модель
    ├── games/                   # ⚠️ TODO
    ├── registrations/           # ⚠️ TODO
    └── core/                    # ⚠️ TODO
```
---
⚠️ ВАЖНО: Модель User
Модель User следует всем правилам из `engineering_rules.md`:
✅ Docstrings
✅ related_name для ForeignKey
✅ db_index для частых запросов
✅ Meta класс с ordering
✅ Soft delete (is_active, deleted_at)
✅ str метод
---
🔧 Следующие шаги
Этап 1: Создать модели (TODO)
```python
# apps/games/models.py
class Game:
    - game_date
    - start_time
    - main_limit (default 18)
    - registration_open_at
    - is_open
    - флаги идемпотентности (email_sent и т.д.)

# apps/registrations/models.py  
class GameRegistration:
    - user, game
    - status (main/reserve/cancelled)
    - queue_position
    - source (player/admin/auto)
    - UniqueConstraint!
    
class RegistrationEvent:
    - registration
    - event_type
    - old_status, new_status
    - performed_by
```
Этап 2: Создать services
```python
# apps/registrations/services.py
- rebuild_queue_internal()
- rebuild_queue_standalone()
- register_user()
- cancel_registration()
```
Этап 3: Views + Templates
```python
# apps/games/views.py
- HomeView (список игр)
- GameDetailView (детали игры)
- RegisterView (запись на игру)
```
Этап 4: Cron jobs
```python
# apps/games/cron.py
- OpenRegistrationJob (Пн 00:01)
- CloseRegistrationJob (Ср 17:00)
- SendRemindersJob (Вт 09:45)

# apps/registrations/cron.py
- PromoteFromReserveJob (каждые 5 мин)
```
---
📚 Документация
Техническое задание
Правила разработки
Инструкция по настройке
---
🐛 Troubleshooting
Ошибка импорта User
```python
# Используй строку, не импорт
from django.conf import settings
user = models.ForeignKey(settings.AUTH_USER_MODEL, ...)
```
Миграции не применяются
```bash
python manage.py showmigrations
python manage.py migrate app_name zero
python manage.py migrate
```
---
Статус: 🚧 В разработке (базовая структура готова)

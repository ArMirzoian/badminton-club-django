# 🏸 Badminton Club Django

Веб-система для управления записью на игры в бадминтон для закрытого клуба.

## 📋 О проекте

Замена Telegram бота на независимую веб-платформу для записи на игры.

**Ключевые возможности:**
- ✅ Регистрация и одобрение пользователей
- ✅ Запись на игры (основа/резерв/админ-резерв)
- ✅ Автоматическое продвижение из резерва
- ✅ Email уведомления
- ✅ Расписание задач (открытие/закрытие записи)
- ✅ Статистика и рейтинг игроков

## 🚀 Быстрый старт

### Требования

- Python 3.11+
- Docker (для локальной БД)
- Git

### Установка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/YOUR_USERNAME/badminton-club-django.git
cd badminton-club-django

# 2. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# 3. Установить зависимости
pip install -r requirements/dev.txt

# 4. Скопировать переменные окружения
cp .env.example .env
# Отредактируй .env - добавь свои настройки

# 5. Запустить PostgreSQL (Docker)
docker-compose up -d

# 6. Применить миграции
cd backend
python manage.py migrate

# 7. Создать суперпользователя
python manage.py createsuperuser

# 8. Запустить сервер
python manage.py runserver
```

Открой: http://localhost:8000

## 📁 Структура проекта

```
badminton-club-django/
├── docs/                          # Документация
│   ├── 00-project_context.md     # Техническое задание
│   ├── engineering_rules.md      # Правила разработки
│   └── setup.md                  # Инструкция по настройке
├── backend/                       # Django приложение
│   ├── manage.py
│   ├── config/                   # Настройки проекта
│   │   ├── settings/
│   │   │   ├── base.py          # Базовые настройки
│   │   │   ├── dev.py           # Для разработки
│   │   │   └── prod.py          # Для production
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── apps/                     # Django приложения
│       ├── accounts/            # Пользователи
│       ├── games/               # Игры
│       ├── registrations/       # Записи на игры
│       └── core/                # Общие утилиты
├── requirements/                 # Зависимости Python
│   ├── base.txt                 # Базовые
│   ├── dev.txt                  # Для разработки
│   └── prod.txt                 # Для production
├── docker-compose.yml            # Локальная БД
├── .env.example                  # Пример настроек
├── .gitignore
└── README.md
```

## 🔧 Разработка

### Создание миграций

```bash
python manage.py makemigrations
python manage.py migrate
```

### Запуск тестов

```bash
pytest
```

### Форматирование кода

```bash
black backend/
isort backend/
```

## 📚 Документация

- [Техническое задание](docs/00-project_context.md) - полное описание проекта
- [Правила разработки](docs/engineering_rules.md) - стандарты кода
- [Инструкция по настройке](docs/setup.md) - детальная установка

## 🚀 Деплой

### Render.com (бесплатно)

1. Создай аккаунт на [Render.com](https://render.com)
2. Подключи GitHub репозиторий
3. Render автоматически развернёт по `render.yaml`

Подробнее: [docs/setup.md](docs/setup.md)

## 🛠 Технологии

- **Backend:** Django 5.0
- **БД:** PostgreSQL 15
- **Задачи:** django-cron
- **Email:** Gmail SMTP
- **Frontend:** Django Templates + Tailwind CSS
- **Хостинг:** Render.com

## 📝 Миграция из Telegram бота

Скрипт для переноса пользователей:

```bash
python manage.py migrate_from_bot
```

Подробнее в [docs/setup.md](docs/setup.md)

## 🤝 Contributing

1. Fork проекта
2. Создай feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Открой Pull Request

**Важно:** Следуй [engineering_rules.md](docs/engineering_rules.md)

## 📄 Лицензия

MIT License

## 👥 Авторы

- Артур М. - Initial work

## 📞 Контакты

Вопросы и предложения: [создай Issue](https://github.com/YOUR_USERNAME/badminton-club-django/issues)

---

**Статус:** 🚧 В разработке

**Версия:** 0.1.0 (MVP)

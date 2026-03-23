# Project Context: Badminton Club Django

> **Single Source of Truth для всех AI-ассистентов**
> Последнее обновление: 2025-03-23

---

## 🎯 О проекте

### Что это?
Веб-система для управления записью на игры в бадминтон для закрытого клуба.

### Зачем?
Telegram бот блокируется в РФ → нужна независимая веб-платформа.

### Кто пользователи?
- **Игроки** — участники закрытого клуба, количество определяется администраторами
- **Администраторы** — пользователи с правами управления системой (обычно 2-3 человека)
- **Гости** — потенциальные игроки до одобрения регистрации

---

## 🏗️ Архитектура

### Технологический стек
```
Backend:  Django 5.0 + PostgreSQL
Tasks:    Celery + Redis
Frontend: Django Templates + Tailwind CSS
Hosting:  Render.com (free tier для MVP, платный для production)
```

**⚠️ ВАЖНО: Хостинг стратегия**
```
MVP / Тестирование:
✅ Render.com Free Tier
   - Достаточно для разработки
   - Бесплатно
   - Ограничения: sleep после 15 мин неактивности
   
Production:
✅ Render.com Starter ($7/мес) или Professional
   - Без sleep
   - Больше CPU/RAM
   - Стабильность 99.9%
   
Альтернативы:
✅ Railway.app ($5-20/мес)
✅ Fly.io (от $0)
✅ VPS (Hetzner €4.5/мес, больше контроля)

ПРАВИЛО:
- Free tier = только для разработки и тестирования
- Production = платный план обязателен
```

### Основные модули (Django Apps)
```
accounts       - Пользователи, регистрация
games          - Игры, расписание
registrations  - Записи, основа, резерв
announcements  - Объявления админов
comments       - Комментарии к играм
notifications  - Email уведомления
audit          - Журнал действий
core           - Общие настройки
```

---

## 📋 Бизнес-логика

### Правила записи

1. **Лимиты:**
   - Основа: game.main_limit (по умолчанию 18, настраивается админом)
   - Резерв: неограничен
   - Админ-резерв: для игроков без Telegram ID

2. **Расписание:**
   - Понедельник 00:01 (МСК) - запись открывается
   - Среда 17:00 (МСК) - запись закрывается
   - Среда 21:00-23:00 - игра

3. **Распределение:**
   - Первые game.main_limit записавшихся → Основа
   - С (main_limit + 1)-го → Резерв
   - При отмене из основы → первый из резерва автоматически поднимается

4. **Уведомления:**
   - Email при открытии записи
   - Email при переводе из резерва в основу
   - Напоминание во вторник 09:45
   - Напоминание в день игры

⚠️ **ВАЖНО:** main_limit может меняться!
```python
# Админ может изменить лимит для конкретной игры
game.main_limit = 20  # Например, на праздник
game.save()
rebuild_queue_standalone(game.id)  # Автоматически пересчитает

# Или вернуть к дефолту
game.main_limit = 18
game.save()
rebuild_queue_standalone(game.id)
```

---

## 👥 Роли пользователей

### Гость
```
- Видит только страницу входа/регистрации
- Может зарегистрироваться (ожидает одобрения)
```

### Игрок
```
- Записываться на игры
- Отменять запись
- Писать комментарии
- Читать объявления
- Видеть свою статистику
```

### Администратор
```
- Всё что игрок +
- Создавать/редактировать игры
- Утверждать регистрации
- Управлять составом (основа/резерв)
- Публиковать объявления
- Добавлять игроков вручную
```

---

## 🔐 Критические требования

### Безопасность
```
✅ Закрытая регистрация (только с одобрением админа)
✅ HTTPS обязательно
✅ Хеширование паролей (bcrypt)
✅ CSRF защита
✅ SQL injection защита (Django ORM)
✅ Транзакции для записи (race conditions)
```

### Производительность
```
✅ Запись открывается в Пн 00:01 → 50 человек жмут одновременно
✅ select_for_update() при записи
✅ Кеширование списков (Redis)
```

### Надёжность
```
✅ Celery для фоновых задач (email, напоминания)
✅ Retry при ошибке отправки email
✅ Журнал всех действий (AuditLog)
✅ История изменений записи (RegistrationEvent)
```

---

## 📐 Ключевые сущности

### User (Custom Django User)
```python
- email (unique, login)
- display_name (показывается в списках)
- telegram_id (опционально)
- approval_status (pending/approved/rejected)
- role (player/admin)
```

### Game
```python
- game_date, start_time
- registration_open_at, registration_close_at
- main_limit (default: 18)
- status (draft/open/closed/completed)
```

### GameRegistration
```python
- user, game
- status (main/reserve/cancelled)
- queue_position (порядковый номер)
- source (player/admin/auto_promotion)
- registered_at
- is_active (для soft delete)

# 🔥 КРИТИЧНО: Constraint на дубли
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['user', 'game'],
            condition=models.Q(is_active=True),
            name='unique_active_registration'
        )
    ]
    # ✅ Гарантия: один пользователь = одна активная запись на игру
```

### RegistrationEvent
```python
- registration
- event_type (created/moved_to_main/cancelled/...)
- old_status, new_status
- performed_by_user / performed_by_system
```

---

## 🎨 Принципы разработки

### Code Style
```
✅ PEP 8 для Python
✅ Django naming conventions
✅ Docstrings для всех функций
✅ Type hints где возможно
```

### Архитектурные паттерны
```
✅ Service Layer (вся логика в services.py)
✅ Repository pattern (queries в managers.py)
✅ Django ORM (НЕ используем raw SQL)
✅ Celery Tasks (async операции)
```

### Тестирование
```
✅ Unit tests для services
✅ Integration tests для views
✅ Pytest + Django fixtures
✅ Минимум 80% coverage
```

---

## 🔄 Ключевые процессы

### 🔥 КРИТИЧНО: Idempotency (идемпотентность)

**ВСЕ Celery задачи ОБЯЗАТЕЛЬНО идемпотентные!**

```python
@shared_task
def send_registration_open_email(game_id: int):
    """
    ⚠️ ДОЛЖНА быть идемпотентной!
    
    Проблема без идемпотентности:
    - Task упал
    - Celery retry
    - Email отправлен дважды ❌
    
    Решение:
    1. Проверить "уже выполнено?"
    2. Выполнить если нет
    3. Пометить как выполнено
    """
    game = Game.objects.get(id=game_id)
    
    # ✅ Проверка идемпотентности
    if game.registration_open_email_sent:
        logger.info(f"Email already sent for game {game_id}")
        return
    
    # Отправка email
    for user in User.objects.filter(is_active=True):
        send_mail(...)
    
    # ✅ Пометка выполнения
    game.registration_open_email_sent = True
    game.save(update_fields=['registration_open_email_sent'])


@shared_task
def promote_from_reserve_task(game_id: int):
    """
    ⚠️ Идемпотентность через проверку состояния!
    
    Не используем флаг, а проверяем текущее состояние:
    - Если есть места в основе И есть резервисты → продвигаем
    - Иначе → ничего не делаем
    
    Можно вызывать сколько угодно раз безопасно.
    """
    with transaction.atomic():
        game = Game.objects.select_for_update().get(id=game_id)
        
        main_count = game.registrations.filter(
            status='main', is_active=True
        ).count()
        
        # ✅ Проверка: нужно ли продвижение?
        if main_count >= game.main_limit:
            return  # Места нет, продвижение не нужно
        
        first_reserve = game.registrations.filter(
            status='reserve', is_active=True
        ).order_by('queue_position').first()
        
        if not first_reserve:
            return  # Резервистов нет
        
        # Продвижение (идемпотентное)
        first_reserve.status = 'main'
        first_reserve.save()
        
        # Rebuild queue (тоже идемпотентная!)
        rebuild_queue(game_id)
```

**Флаги идемпотентности в модели Game:**
```python
class Game(models.Model):
    # ... другие поля
    
    # Флаги выполнения задач
    registration_open_email_sent = models.BooleanField(default=False)
    reminder_tuesday_sent = models.BooleanField(default=False)
    reminder_game_day_sent = models.BooleanField(default=False)
    registration_closed_email_sent = models.BooleanField(default=False)
```

**ПРАВИЛО:**
```
❌ Задача не должна полагаться на "вызов только один раз"
✅ Задача проверяет "уже выполнено?" и безопасна при повторе
```

### Процесс записи
```
1. Игрок нажимает "Записаться"
2. Проверка: одобрен ли, запись открыта ли
3. Транзакция с select_for_update()
4. Если места в основе < main_limit → main
5. Иначе → reserve
6. Сохранение + RegistrationEvent
7. ✅ Пересборка очереди (rebuild_queue_internal)
8. ✅ Commit транзакции
9. ⏰ Email уведомление (через transaction.on_commit + Celery)

⚠️ ВАЖНО: Email НЕ внутри транзакции!
- Транзакция: шаги 3-8 (быстро, только БД)
- Email: шаг 9 (асинхронно, после commit)
```

### Процесс отмены
```
1. Игрок нажимает "Отменить"
2. Транзакция с select_for_update()
3. Статус → cancelled
4. RegistrationEvent
5. Если был в основе → вызов promote_from_reserve()
6. ✅ Commit транзакции
7. ⏰ Email тому кто поднялся (через on_commit + Celery)

⚠️ ВАЖНО: Все уведомления ПОСЛЕ commit через Celery
```

**Детальный код процесса записи:**
```python
@transaction.atomic
def register_user_for_game(user, game):
    """
    КРИТИЧЕСКАЯ СЕКЦИЯ: только БД операции
    """
    # Блокировка
    game = Game.objects.select_for_update().get(id=game.id)
    
    # Валидация
    if GameRegistration.objects.filter(
        user=user, game=game, is_active=True
    ).exists():
        raise ValidationError("Already registered")
    
    # Определение статуса
    main_count = game.registrations.filter(
        status='main', is_active=True
    ).count()
    status = 'main' if main_count < game.main_limit else 'reserve'
    
    # Создание
    registration = GameRegistration.objects.create(
        user=user,
        game=game,
        status=status,
        source='player'
    )
    
    # Событие
    RegistrationEvent.objects.create(
        registration=registration,
        event_type='created',
        new_status=status,
        performed_by_user=user
    )
    
    # Пересборка очереди
    rebuild_queue_internal(game.id)
    
    # ✅ Транзакция завершается ЗДЕСЬ (commit)
    
    # ⏰ Email ПОСЛЕ commit (через on_commit)
    transaction.on_commit(
        lambda: send_registration_confirmation.delay(registration.id)
    )
    
    return registration
```

### Автопродвижение
```python
@shared_task
def promote_from_reserve_task(game_id: int):
    """
    Идемпотентность через проверку текущего состояния.
    
    НЕ меняет статус вручную!
    Только вызывает rebuild_queue() если нужно продвижение.
    
    Можно вызывать сколько угодно раз безопасно.
    """
    with transaction.atomic():
        game = Game.objects.select_for_update().get(id=game_id)
        
        main_count = game.registrations.filter(
            status='main', is_active=True
        ).count()
        
        # ✅ Проверка: нужно ли продвижение?
        if main_count >= game.main_limit:
            return {'status': 'no_space'}
        
        reserve_count = game.registrations.filter(
            status='reserve', is_active=True
        ).count()
        
        if reserve_count == 0:
            return {'status': 'no_reserves'}
        
        # ✅ ПРАВИЛЬНО: Только rebuild_queue!
        # Он сам пересчитает статусы и продвинет первого резервиста
        rebuild_queue_internal(game.id)
        
        # Находим кто был продвинут (для уведомления)
        promoted = game.registrations.filter(
            status='main',
            is_active=True
        ).order_by('-queue_position').first()  # Последний в основе = только что продвинутый
    
    # ⏰ Email вне транзакции
    if promoted and promoted.user_id:
        send_promoted_email.delay(promoted.id)
    
    return {'status': 'promoted', 'user_id': promoted.user_id if promoted else None}
```

**ПРАВИЛО:**
```
❌ НЕ делать: reserve.status = 'main'; reserve.save()
✅ ДЕЛАТЬ: rebuild_queue_internal(game_id)

Почему:
- rebuild_queue() - единственный источник истины
- Избегаем дублирования логики
- Гарантия консистентности
```

### 🔥 КРИТИЧЕСКИ ВАЖНО: Queue Consistency

**ЕДИНСТВЕННЫЙ ИСТОЧНИК ИСТИНЫ:**
```python
def rebuild_queue(game_id: int) -> None:
    """
    ⚠️ КЛЮЧЕВАЯ ФУНКЦИЯ СИСТЕМЫ!
    
    Единственный источник истины для состояния очереди.
    ВСЕГДА вызывается после ЛЮБОГО изменения состава.
    
    Гарантирует:
    - Никаких "поехавших" позиций
    - Консистентность main/reserve статусов
    - Идемпотентность (можно вызывать сколько угодно)
    
    Алгоритм:
    1. SELECT всех активных записей (is_active=True, status != 'cancelled')
    2. ORDER BY registered_at ASC (первый записался = первый в очереди)
    3. Присвоить queue_position = 1, 2, 3, ...
    4. Первым main_limit записям → status = 'main'
    5. Остальным → status = 'reserve'
    6. Сохранить изменения
    7. Создать RegistrationEvent для изменённых
    
    Вызывается ВСЕГДА после:
    - Новой записи
    - Отмены записи
    - Удаления админом
    - Изменения main_limit
    - Ручного перемещения
    - Импорта данных
    
    Transaction:
    - ОБЯЗАТЕЛЬНО в @transaction.atomic
    - С select_for_update() на Game
    """
```

**ПРАВИЛО:**
```
❌ ЗАПРЕЩЕНО вручную менять queue_position или status
✅ ВСЕГДА через rebuild_queue(game_id)
```

---

## 🚀 Миграция из Telegram бота

### Что переносим:
```
1. KNOWN_USERS (актуальный состав игроков из текущей системы) → User модель
2. storage.json (текущая запись) → GameRegistration
3. Google Sheets (статистика) → БД для отчётов
4. APScheduler расписание → Celery Beat
5. Email шаблоны → Django templates
```

### Скрипты миграции:
```
scripts/migrate_from_bot.py
scripts/import_users.py
scripts/import_statistics.py
```

---

## 📧 Email уведомления

### Типы:
```
1. registration_approved    - регистрация одобрена
2. registration_open        - запись открыта (Пн 00:01)
3. registered_main          - записан в основу
4. registered_reserve       - записан в резерв
5. promoted_to_main         - переведён из резерва
6. reminder_tuesday         - напоминание (Вт 09:45)
7. reminder_game_day        - напоминание в день игры
8. game_cancelled           - игра отменена
9. announcement_important   - важное объявление
```

### Отправка:
```python
# Через Celery (асинхронно)
@shared_task
def send_email_notification(user_id, template_name, context):
    ...
```

---

## 📊 Мониторинг и логи

### Что логируем:
```
✅ Все действия админов (AuditLog)
✅ Все изменения записей (RegistrationEvent)
✅ Ошибки отправки email (Notification.status)
✅ Celery task failures
✅ Django errors (Sentry опционально)
```

---

## 🎨 UI/UX Требования

### 🔥 КРИТИЧНО: Аудитория 50+ лет

**Проблема:** Пользователи возраста 25-60 лет, не все tech-savvy

**Решение: МАКСИМАЛЬНАЯ простота**

### Принципы дизайна:

**1. Одна кнопка на действие**
```html
<!-- ✅ ПРАВИЛЬНО -->
<button class="btn-primary btn-lg">
    ✅ Записаться на игру
</button>

<!-- ❌ НЕПРАВИЛЬНО -->
<div class="dropdown">
    <button>Действия ▼</button>
    <ul>
        <li>Записаться</li>
        <li>В резерв</li>
        <li>Отменить</li>
    </ul>
</div>
```

**2. Крупный текст**
```css
/* ✅ Минимальные размеры */
body {
    font-size: 18px;  /* Не меньше! */
}

.btn {
    font-size: 20px;
    padding: 15px 30px;  /* Большая область клика */
    min-height: 60px;
}

h1 {
    font-size: 32px;
}
```

**3. Контрастные цвета**
```css
/* ✅ Высокий контраст для читаемости */
.btn-primary {
    background: #007bff;  /* Яркий синий */
    color: #ffffff;       /* Белый текст */
    /* Контраст: 4.5:1 minimum */
}

.status-main {
    background: #28a745;  /* Зелёный */
    color: white;
}

.status-reserve {
    background: #ffc107;  /* Жёлтый */
    color: #000;          /* Чёрный текст */
}
```

**4. Минимум кликов**
```
Цель пользователя: Записаться на игру

✅ ПРАВИЛЬНО (2 клика):
1. Открыл главную → видит игру
2. Нажал "Записаться" → готово

❌ НЕПРАВИЛЬНО (5+ кликов):
1. Открыл главную
2. Нажал "Игры"
3. Выбрал дату
4. Открыл карточку игры
5. Нажал "Записаться"
6. Подтвердил в модалке
```

**5. Без вложенных меню**
```html
<!-- ✅ ПРАВИЛЬНО: Плоская навигация -->
<nav>
    <a href="/">Главная</a>
    <a href="/profile">Профиль</a>
    <a href="/stats">Статистика</a>
</nav>

<!-- ❌ НЕПРАВИЛЬНО: Вложенные dropdown -->
<nav>
    <div class="dropdown">
        <a>Меню ▼</a>
        <ul>
            <li>
                <a>Игры ▶</a>
                <ul>
                    <li>Ближайшие</li>
                    <li>Прошедшие</li>
                </ul>
            </li>
        </ul>
    </div>
</nav>
```

**6. Явные состояния**
```html
<!-- ✅ ПРАВИЛЬНО: Чёткий статус -->
<div class="status-card status-main">
    <h2>✅ ВЫ В ОСНОВЕ</h2>
    <p>Место №5 из 18</p>
    <button>❌ Отменить запись</button>
</div>

<!-- ❌ НЕПРАВИЛЬНО: Непонятно -->
<div>
    <span class="badge">Registered</span>
    <small>Position: 5/18</small>
</div>
```

**7. Мобильная версия ПЕРВИЧНА**
```
Mobile-first подход:
✅ Дизайн сначала для телефона
✅ Потом адаптация под десктоп
✅ Крупные кнопки удобны на touch
✅ Вертикальные списки (не таблицы)
```

**8. Быстрая загрузка**
```
✅ Максимум 2 секунды до первого контента
✅ Минимум JavaScript
✅ Никаких SPA-фреймворков (React/Vue не нужны)
✅ Django templates + Tailwind достаточно
```

### Пример главной страницы:

```html
<!-- Идеальная главная для возрастной аудитории -->
<main style="max-width: 800px; margin: 0 auto; padding: 20px;">
    
    <!-- Крупный заголовок -->
    <h1 style="font-size: 32px; margin-bottom: 30px;">
        🏸 Запись на игру
    </h1>
    
    <!-- Карточка игры - всё на виду -->
    <div style="
        background: white;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 30px;
    ">
        <h2 style="font-size: 28px; margin-bottom: 20px;">
            Среда, 26 марта 2025
        </h2>
        
        <p style="font-size: 20px; line-height: 1.6;">
            📍 Электролитный пр.3, стр.5<br>
            ⏰ 21:00 - 23:00<br>
            💰 800 руб.
        </p>
        
        <!-- Ваш статус - крупно и ярко -->
        <div style="
            background: #28a745;
            color: white;
            padding: 20px;
            border-radius: 8px;
            font-size: 24px;
            text-align: center;
            margin: 20px 0;
        ">
            ✅ ВЫ ЗАПИСАНЫ (ОСНОВА, место №5)
        </div>
        
        <!-- Одна большая кнопка -->
        <button style="
            width: 100%;
            padding: 20px;
            font-size: 22px;
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        ">
            ❌ Отменить запись
        </button>
    </div>
    
    <!-- Состав - простой список -->
    <div style="background: white; padding: 30px; border-radius: 10px;">
        <h3 style="font-size: 24px; margin-bottom: 15px;">
            🟢 Основа (18 мест):
        </h3>
        <ol style="font-size: 18px; line-height: 2;">
            <li>Артур М.</li>
            <li>Александр З.</li>
            <li>Владимир Б.</li>
            <!-- ... -->
        </ol>
        
        <h3 style="font-size: 24px; margin: 30px 0 15px;">
            🟡 Резерв (3 человека):
        </h3>
        <ol style="font-size: 18px; line-height: 2;">
            <li>Иван П.</li>
            <li>Мария К.</li>
            <li>Сергей Т.</li>
        </ol>
    </div>
    
</main>
```

**ПРАВИЛО:**
```
❌ Красивый дизайн ≠ Хороший UX для этой аудитории
✅ Простой, крупный, контрастный = Идеально
```

### Фаза 1 (MVP - 4 недели):
```
✅ User model + регистрация
✅ Game model
✅ GameRegistration + логика
✅ Базовые views
✅ Email уведомления
✅ Celery tasks
✅ Деплой на Render
```

### Фаза 2 (2 недели):
```
✅ Комментарии
✅ Объявления
✅ Статистика
✅ Миграция данных из бота
```

### Фаза 3 (1 неделя):
```
✅ Полировка UI
✅ Тестирование
✅ Документация
```

---

## ⚠️ Известные проблемы

### Race Conditions

**🔥 КРИТИЧНО: Одновременная активность при открытии записи**

```
Проблема: Понедельник 00:01 - запись открывается
          В момент открытия возможна высокая одновременная активность игроков
          
Опасность без защиты:
- Два человека на одно место
- "Поехавшая" очередь
- Дублирующиеся записи
```

**Решение 1: Database-level (ОБЯЗАТЕЛЬНО)**
```python
@transaction.atomic
def register_user_for_game(user, game):
    # ✅ Блокировка строки игры
    game = Game.objects.select_for_update().get(id=game.id)
    
    # ✅ Проверка дубля на уровне БД
    if GameRegistration.objects.filter(
        user=user,
        game=game,
        is_active=True
    ).exists():
        raise ValidationError("Already registered")
    
    # ✅ Атомарное создание
    registration = GameRegistration.objects.create(
        user=user,
        game=game,
        ...
    )
    
    # ✅ Пересборка очереди в той же транзакции
    rebuild_queue(game.id)
    
    return registration
```

**Решение 2: Rate Limiting (ОБЯЗАТЕЛЬНО)**

**Решение 3: Frontend Debounce (дополнительно)**
```javascript
// Защита от случайных двойных кликов
let isSubmitting = false;

document.querySelector('#register-btn').addEventListener('click', async (e) => {
    if (isSubmitting) {
        return; // Игнорируем повторные клики
    }
    
    isSubmitting = true;
    e.target.disabled = true;
    e.target.textContent = 'Записываемся...';
    
    try {
        await fetch('/register/', {method: 'POST'});
    } finally {
        isSubmitting = false;
    }
});
```

**Решение 4: Optimistic UI Lock**
```python
# В cache ставим временный lock
def register_with_lock(user_id, game_id):
    lock_key = f'registration_lock_{user_id}_{game_id}'
    
    # ✅ Проверяем lock
    if cache.get(lock_key):
        raise ValidationError("Запись уже в процессе")
    
    # ✅ Ставим lock на 10 секунд
    cache.set(lock_key, True, timeout=10)
    
    try:
        # Выполняем запись
        registration = register_user_for_game(user_id, game_id)
        return registration
    finally:
        # ✅ Снимаем lock
        cache.delete(lock_key)
```

**ПРАВИЛО:**
```
❌ Полагаться только на frontend защиту
✅ Многоуровневая защита: БД + Backend + Frontend
```
```
Проблема: 50 человек жмут "Записаться" одновременно в Пн 00:01
Решение: select_for_update() + transaction.atomic()
```

### Email Delivery

**🔥 КРИТИЧНО: Email - слабое место системы**

```
Проблема: Gmail SMTP лимит 500/день
Решение: Многоуровневая стратегия
```

**Фаза 1 (MVP):**
```python
# Gmail SMTP (бесплатно)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

Лимит: 500 email/день
Оценка: Для текущего состава клуба и плановой частоты уведомлений 
        лимита достаточно для MVP
```

**Фаза 2 (если нужно больше):**
```python
# SendGrid / Mailgun
# SendGrid: 100 email/день бесплатно, $15/мес за 40K
# Mailgun: 5000 email/месяц бесплатно

EMAIL_BACKEND = 'sendgrid.EmailBackend'
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
```

**🔥 Retry Policy (ОБЯЗАТЕЛЬНО):**
```python
@shared_task(
    bind=True,
    autoretry_for=(SMTPException, ConnectionError),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True,
    retry_jitter=True
)
def send_email_with_retry(self, to_email, subject, message):
    """
    Автоматический retry:
    - Попытка 1: сразу
    - Попытка 2: через 60 сек
    - Попытка 3: через 120 сек (backoff)
    - Попытка 4: через 240 сек (backoff + jitter)
    
    Если все неудачно → записать в Notification.status = 'failed'
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False
        )
        
        # ✅ Успешная отправка
        Notification.objects.filter(
            user__email=to_email,
            type=subject
        ).update(
            status='sent',
            sent_at=timezone.now()
        )
        
    except Exception as e:
        # ❌ Ошибка отправки
        Notification.objects.filter(
            user__email=to_email,
            type=subject
        ).update(
            status='failed',
            error_message=str(e)
        )
        raise  # Retry
```

**Fallback Provider:**
```python
def send_email_with_fallback(to_email, subject, message):
    """
    Пытается отправить через primary, при ошибке → fallback
    """
    try:
        # Primary: Gmail
        send_via_gmail(to_email, subject, message)
    except Exception as e:
        logger.warning(f"Gmail failed: {e}, trying SendGrid")
        try:
            # Fallback: SendGrid
            send_via_sendgrid(to_email, subject, message)
        except Exception as e2:
            logger.error(f"Both providers failed: {e2}")
            # Записать в БД для ручной обработки
            Notification.objects.create(
                user=User.objects.get(email=to_email),
                type='failed_delivery',
                status='failed',
                error_message=f"Gmail: {e}, SendGrid: {e2}"
            )
```

**Мониторинг доставки:**
```python
# Admin dashboard: кому не дошло
failed_notifications = Notification.objects.filter(
    status='failed',
    created_at__gte=timezone.now() - timedelta(days=7)
)

# Ручная переотправка
@admin.action(description='Retry failed emails')
def retry_failed_emails(modeladmin, request, queryset):
    for notification in queryset.filter(status='failed'):
        send_email_with_retry.delay(
            notification.user.email,
            notification.subject,
            notification.body
        )
```

**ПРАВИЛО:**
```
❌ НИКОГДА fail_silently=True (молча проглатывать ошибки)
✅ ВСЕГДА retry + fallback + логирование
```

### Timezone

**🔥 КРИТИЧНО: Часовой пояс**

**ПРАВИЛО: Для всей системы используется часовой пояс Europe/Moscow**

```
Все расписания, проверки времени, уведомления и отображение дат/времени 
выполняются в часовом поясе Москвы.

Использование naive datetime ЗАПРЕЩЕНО.
```

**Настройка Django:**
```python
# settings.py
TIME_ZONE = 'Europe/Moscow'  # ✅ Единый часовой пояс проекта
USE_TZ = True                # ✅ Timezone-aware datetimes обязательны

# Celery тоже в Moscow timezone
CELERY_TIMEZONE = 'Europe/Moscow'
CELERY_ENABLE_UTC = False
```

**Работа с датами/временем:**
```python
from django.utils import timezone
import pytz

MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# ✅ ПРАВИЛЬНО: Получить текущее время
now = timezone.now()  # Автоматически в настроенной таймзоне (МСК)

# ✅ ПРАВИЛЬНО: Создание времени МСК
from datetime import datetime, time, date

game_date = date(2025, 4, 2)  # Среда
registration_open = datetime.combine(
    game_date - timedelta(days=2),  # Понедельник
    time(0, 1),  # 00:01
    tzinfo=MOSCOW_TZ
)

game = Game.objects.create(
    game_date=game_date,
    start_time=time(21, 0),  # 21:00
    registration_open_at=registration_open
)

# ✅ ПРАВИЛЬНО: Проверка времени
if timezone.now() >= game.registration_open_at:
    # Запись открыта
```

```python
# ❌ НЕПРАВИЛЬНО: Локальное время сервера
from datetime import datetime
now = datetime.now()  # Зависит от настроек сервера!

# ❌ НЕПРАВИЛЬНО: Naive datetime (без timezone)
game.registration_open_at = datetime(2025, 4, 1, 0, 1)  # Без tzinfo!
```

**Celery Beat расписание:**
```python
from celery.schedules import crontab

# Все расписания в Moscow timezone (настроено в CELERY_TIMEZONE)
app.conf.beat_schedule = {
    'open-registration': {
        'task': 'games.tasks.open_registration',
        'schedule': crontab(
            day_of_week=0,  # Monday
            hour=0,         # 00:01 МСК
            minute=1
        ),
    },
    'close-registration': {
        'task': 'games.tasks.close_registration',
        'schedule': crontab(
            day_of_week=2,  # Wednesday
            hour=17,        # 17:00 МСК
            minute=0
        ),
    },
    'reminder-tuesday': {
        'task': 'games.tasks.send_reminders',
        'schedule': crontab(
            day_of_week=1,  # Tuesday
            hour=9,         # 09:45 МСК
            minute=45
        ),
    },
}
```

**Отображение в templates:**
```django
{# Django автоматически использует TIME_ZONE из settings #}
{{ game.registration_open_at|date:"d.m.Y H:i" }}
{# Отобразится в Moscow timezone #}

{# Явная конвертация (если нужно) #}
{% load tz %}
{% timezone "Europe/Moscow" %}
    {{ game.registration_open_at|date:"d.m.Y H:i" }}
{% endtimezone %}
```

**ИСТОЧНИК ВРЕМЕНИ ДЛЯ ВСЕЙ СИСТЕМЫ:**
```
Django:           TIME_ZONE = 'Europe/Moscow'
Celery:           CELERY_TIMEZONE = 'Europe/Moscow'
Celery Beat:      Расписания в МСК (hour=0 = 00:00 МСК)
БД:               Timezone-aware (PostgreSQL timestamptz)
Отображение:      Автоматически МСК
Логика:           timezone.now() → МСК
```

**⚠️ ВАЖНО: Переход на летнее/зимнее время**
```
В России с 2014 года нет перехода на летнее время.
Europe/Moscow = UTC+3 круглый год.
Проблем с DST не будет.
```

**ПРАВИЛО:**
```
✅ ВСЕГДА: timezone.now() для получения текущего времени
✅ ВСЕГДА: tzinfo=MOSCOW_TZ при создании datetime
❌ НИКОГДА: datetime.now() без timezone
❌ НИКОГДА: naive datetime (без tzinfo)
```

---

## 🔗 Связанные документы

- [Architecture](./01-architecture.md) - детальная архитектура
- [Database Schema](./03-database_schema.md) - схема БД
- [Business Logic](./02-business_logic.md) - бизнес-правила
- [API Design](./04-api_design.md) - дизайн API (если нужен)
- [Deployment](./05-deployment.md) - деплой на Render

---

---

## 🟡 Дополнительные улучшения (не критично для MVP)

### 1. Notification Preferences

**Проблема:** Не все хотят получать ВСЕ уведомления

**Решение:**
```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Настройки уведомлений
    notify_registration_open = models.BooleanField(default=True)
    notify_promoted_to_main = models.BooleanField(default=True)
    notify_reminder_tuesday = models.BooleanField(default=True)
    notify_reminder_game_day = models.BooleanField(default=False)  # По умолчанию выкл
    notify_announcements = models.BooleanField(default=True)
```

**UI:**
```
Настройки → Уведомления
☑ Запись открыта
☑ Переведён из резерва в основу
☑ Напоминание во вторник
☐ Напоминание в день игры (может быть навязчиво)
☑ Важные объявления
```

---

### 2. Admin Override Logic

**Вопрос:** Может ли админ нарушать очередь?

**Ответ: Админ МОЖЕТ нарушать бизнес-правила, но ТЕХНИЧЕСКИ через сервис**

```python
# ❌ НЕПРАВИЛЬНО: Прямое изменение (нарушает правило "только через rebuild_queue")
def admin_move_to_main(admin_user, registration):
    registration.status = 'main'  # ❌ Вручную!
    registration.save()
    # Очередь "поедет"!

# ✅ ПРАВИЛЬНО: Через сервис
class RegistrationService:
    @staticmethod
    @transaction.atomic
    def admin_override_to_main(admin_user, registration):
        """
        Админ может нарушать бизнес-правила:
        - Перевести в основу вне очереди
        - Превысить main_limit
        
        Но ТЕХНИЧЕСКИ:
        - Идёт через сервис
        - Завершается rebuild_queue()
        - Логируется в AuditLog
        """
        game = Game.objects.select_for_update().get(id=registration.game_id)
        
        # Проверка: превышение лимита?
        if game.registrations.filter(status='main', is_active=True).count() >= game.main_limit:
            # Админ может превысить лимит
            AuditLog.objects.create(
                admin=admin_user,
                action='override_main_limit',
                description=f'Added {registration.user} to full main roster'
            )
        
        # НЕ меняем вручную! Пометим флагом для rebuild_queue
        registration.admin_priority = True  # Специальный флаг
        registration.save()
        
        # ✅ Пересборка с учётом admin_priority
        rebuild_queue_internal(game.id)
        
        # Логируем действие админа
        RegistrationEvent.objects.create(
            registration=registration,
            event_type='admin_override',
            new_status=registration.status,  # Установлен в rebuild_queue
            performed_by_user=admin_user
        )

# Модифицированная rebuild_queue учитывает admin_priority
def rebuild_queue_internal(game_id):
    """
    Сортирует с учётом:
    1. admin_priority=True (админ переместил) - в начало
    2. registered_at (обычная очередь)
    """
    game = Game.objects.get(id=game_id)
    
    registrations = list(
        game.registrations.filter(is_active=True)
        .exclude(status='cancelled')
        .order_by('-admin_priority', 'registered_at')  # ✅ Приоритет админа
    )
    
    # Дальше стандартная логика...
```

**ПРАВИЛО:**
```
✅ Админ МОЖЕТ нарушать бизнес-правила (превысить лимит, изменить порядок)
✅ Но ТЕХНИЧЕСКИ через сервис + rebuild_queue()
✅ Все изменения логируются в AuditLog
❌ НИКОГДА напрямую registration.status = 'main'
```

---

### 3. Soft Delete vs Hard Delete

**Проблема:** Удалённая запись = потерянная статистика

**Решение: Soft Delete (РЕКОМЕНДУЕТСЯ)**

```python
class GameRegistration(models.Model):
    # ... поля
    
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name='deleted_registrations'
    )

# Вместо .delete()
def soft_delete(registration, deleted_by=None):
    registration.is_active = False
    registration.deleted_at = timezone.now()
    registration.deleted_by = deleted_by
    registration.save()
    
    # Пересобираем очередь (без удалённых)
    rebuild_queue(registration.game_id)

# Запросы только активных
active_registrations = GameRegistration.objects.filter(is_active=True)
```

**Плюсы:**
```
✅ Статистика сохраняется
✅ Можно восстановить ("отменить удаление")
✅ Аудит: кто удалил и когда
```

**Минусы:**
```
⚠️ БД растёт (но для 50 человек не проблема)
⚠️ Нужно всегда фильтровать is_active=True
```

---

### 4. Feature Flags

**Проблема:** Хотим включать/выключать фичи без deploy

**Решение: Простые флаги в БД**

```python
class SiteSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    value_type = models.CharField(max_length=20)  # bool, int, string
    
    @classmethod
    def get_bool(cls, key, default=False):
        try:
            setting = cls.objects.get(key=key)
            return setting.value.lower() == 'true'
        except cls.DoesNotExist:
            return default

# Использование
if SiteSetting.get_bool('feature_comments_enabled', default=True):
    # Показываем комментарии
    ...

if SiteSetting.get_bool('feature_auto_promotion_enabled', default=True):
    # Автопродвижение работает
    promote_from_reserve(game)
```

**Примеры флагов:**
```python
# В Django Admin можно переключать
feature_comments_enabled = True
feature_announcements_enabled = True
feature_auto_promotion_enabled = True
feature_email_notifications_enabled = True
feature_registration_open = True  # Аварийное отключение записи
```

**Плюсы:**
```
✅ Можно выключить сломанную фичу без deploy
✅ Можно тестировать новые фичи на продакшене
✅ A/B тестирование (если понадобится)
```

---

### 5. Admin Notifications (дополнительно)

**Что логировать для админов:**

```python
# Уведомления админам
- Новая регистрация ожидает одобрения
- Игра заполнена (основа полная)
- Резерв пустой, но в основе есть места (Вт 06:00)
- Ошибка отправки email (критично!)
- Celery task failed
```

**Реализация:**
```python
# Telegram bot для админов (опционально)
def notify_admins(message):
    """Отправка в Telegram админам"""
    for admin_id in ADMIN_TELEGRAM_IDS:
        bot.send_message(admin_id, message)

# Или email
def email_admins(subject, message):
    for admin in User.objects.filter(role='admin'):
        send_mail(subject, message, to=[admin.email])
```

---

### 6. Game Templates (шаблоны игр)

**Проблема:** Админ каждую неделю создаёт игру с теми же параметрами

**Решение: Шаблоны**

```python
class GameTemplate(models.Model):
    name = models.CharField(max_length=100)  # "Среда, регулярная"
    day_of_week = models.IntegerField()  # 2 = Wednesday
    start_time = models.TimeField()
    location_name = models.CharField(max_length=200)
    main_limit = models.IntegerField(default=18)
    
    def create_game_from_template(self, date):
        """Создать игру из шаблона"""
        return Game.objects.create(
            game_date=date,
            start_time=self.start_time,
            location_name=self.location_name,
            main_limit=self.main_limit,
            ...
        )
```

**UI:**
```
Админ панель → Создать игру
[Выбрать шаблон: "Среда, регулярная" ▼]
Дата: [26.03.2025]
[Создать] ← Все параметры заполнены автоматически
```

---

## 📝 Changelog

### 2025-03-23 v4 - ФИНАЛЬНАЯ ВЕРСИЯ
**Убраны все конкретные числа, унифицирован timezone:**
- 🔧 Убраны упоминания конкретного количества игроков (50, 55)
- 🔧 "Игроки" → "участники закрытого клуба, количество определяется администраторами"
- 🔧 "50 человек жмут" → "высокая одновременная активность игроков"
- 🔧 "KNOWN_USERS (55 игроков)" → "актуальный состав из текущей системы"
- 🔧 Убраны расчёты email с конкретными числами
- 🔧 Timezone полностью унифицирован: Europe/Moscow ВЕЗДЕ (убрано упоминание UTC в логике)
- 🔧 Упрощён раздел timezone - убрана путаница между "хранением" и "логикой"

### 2025-03-23 v3 - ФИНАЛЬНЫЕ ПРАВКИ
**Исправлены противоречия и неточности:**
- 🔧 Admin Override: теперь через сервис + rebuild_queue (не напрямую)
- 🔧 Процесс записи/отмены: уточнено что email через on_commit + Celery (не синхронно)
- 🔧 Rate limiting: убран лишний cache_page из примера
- 🔧 promote_from_reserve_task: теперь только через rebuild_queue (не меняет статус вручную)
- 🔧 main_limit: исправлен хардкод 18 → game.main_limit (настраивается)
- 🔧 Hosting: добавлена оговорка про Render free tier (только для MVP)

### 2025-03-23 v2 - КРИТИЧЕСКИЕ ПРАВКИ
**Добавлены обязательные разделы:**
- 🔥 Queue Consistency: rebuild_queue() как единственный источник истины
- 🔥 Idempotency: все Celery задачи идемпотентные
- 🔥 Email: retry policy, fallback provider, мониторинг
- 🔥 Constraint: UniqueConstraint для предотвращения дублей
- 🔥 UI/UX: требования для аудитории 50+
- 🔥 Rate Limiting: защита от спама и race conditions

**Добавлены улучшения (не критично для MVP):**
- Notification preferences
- Admin override с аудитом
- Soft delete вместо hard delete
- Feature flags
- Admin notifications
- Game templates

### 2025-03-23 v1
- Initial project context
- Определены роли AI
- Установлены правила разработки

---

**ВАЖНО: Все разделы помеченные 🔥 КРИТИЧНО обязательны для реализации!**

**При любых вопросах об архитектуре, логике или принципах - читай этот файл первым!**

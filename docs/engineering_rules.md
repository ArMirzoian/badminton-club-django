Engineering Rules: Badminton Club Django
> **Правила написания кода для всех AI и разработчиков**
> Эти правила ОБЯЗАТЕЛЬНЫ для Claude, ChatGPT и Cursor
---
🎯 Общие принципы
1. Single Responsibility
```python
# ✅ ПРАВИЛЬНО
class RegistrationService:
    """Только логика записи"""
    def register_user(self, user, game):
        ...

# ❌ НЕПРАВИЛЬНО  
class RegistrationService:
    """Логика записи + email + статистика"""
    def register_user_and_send_email_and_update_stats(self, ...):
        ...
```
2. Explicit is better than implicit
```python
# ✅ ПРАВИЛЬНО
def promote_from_reserve(game: Game) -> Optional[Tuple[int, str]]:
    """
    Продвигает первого из резерва в основу.
    
    Args:
        game: Объект игры
        
    Returns:
        (user_id, user_name) если продвинули, None иначе
    """
    ...

# ❌ НЕПРАВИЛЬНО
def promote(g):
    # что возвращает? что принимает?
    ...
```
---
📐 Naming Conventions
Models
```python
# Singular, CamelCase
class User(models.Model):
    ...

class GameRegistration(models.Model):
    ...
```
Services
```python
# {Entity}Service
class RegistrationService:
    ...

class GameService:
    ...
```
Views
```python
# {action}_{entity}_view
def register_for_game_view(request, game_id):
    ...

def cancel_registration_view(request, game_id):
    ...
```
URLs
```python
# kebab-case
path('games/<int:game_id>/register/', ...),
path('games/<int:game_id>/cancel/', ...),
```
Templates
```python
# snake_case
templates/
├── games/
│   ├── game_detail.html
│   ├── game_list.html
│   └── registration_form.html
```
---
🗄️ Database
Модели
```python
class GameRegistration(models.Model):
    """
    ВСЕГДА:
    - Docstring с описанием
    - related_name для ForeignKey
    - db_index для частых запросов
    - Meta класс с ordering
    - UniqueConstraint для дублей (не unique_together!)
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='game_registrations',  # ✅ ОБЯЗАТЕЛЬНО
        db_index=True
    )
    
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='registrations',
        db_index=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        db_index=True  # ✅ Фильтруем часто
    )
    
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        db_table = 'game_registrations'
        ordering = ['queue_position', 'registered_at']
        
        # 🔥 КРИТИЧНО: UniqueConstraint с condition!
        # Не unique_together - он не поддерживает condition
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'game'],
                condition=models.Q(is_active=True),
                name='unique_active_registration_per_game',
            )
        ]
        
        # ⚠️ ВАЖНО: Constraint - это последняя линия защиты!
        # 
        # Защита работает на трёх уровнях:
        # 
        # 1️⃣ Первичная защита (основная):
        #    @transaction.atomic + select_for_update()
        #    → Предотвращает одновременные изменения
        # 
        # 2️⃣ Бизнес-логика:
        #    if exists() → raise ValidationError
        #    → Предотвращает логические дубли
        # 
        # 3️⃣ Последняя линия (safeguard):
        #    UniqueConstraint на уровне БД
        #    → Если всё остальное не сработало
        # 
        # ✅ UniqueConstraint НЕ заменяет транзакции!
        # ✅ Он дополняет их как финальная гарантия
        # ✅ Полагаться только на constraint = неправильно

# ⚠️ НЕПРАВИЛЬНО: unique_together не поддерживает condition
# unique_together = [['user', 'game', 'is_active']]  # ❌ Так нельзя!
```
Пример правильной защиты от дублей (все 3 уровня):
```python
@transaction.atomic  # 1️⃣ Транзакция
def register_user(user, game):
    # 1️⃣ Блокировка (основная защита от race condition)
    game = Game.objects.select_for_update().get(id=game.id)
    
    # 2️⃣ Бизнес-логика (явная проверка)
    if GameRegistration.objects.filter(
        user=user,
        game=game,
        is_active=True
    ).exists():
        raise ValidationError("Already registered")  # ✅ Понятная ошибка
    
    # 3️⃣ Создание (constraint сработает если что-то пошло не так)
    try:
        registration = GameRegistration.objects.create(
            user=user,
            game=game,
            ...
        )
    except IntegrityError as e:
        # 3️⃣ Constraint сработал (последняя линия)
        if 'unique_active_registration' in str(e):
            raise ValidationError("Already registered (caught by DB)")
        raise
    
    rebuild_queue_internal(game.id)
    return registration
```
Запросы
```python
# ✅ ПРАВИЛЬНО: используем select_related / prefetch_related
registrations = GameRegistration.objects.filter(
    game=game
).select_related('user').all()

# ❌ НЕПРАВИЛЬНО: N+1 queries
registrations = GameRegistration.objects.filter(game=game).all()
for reg in registrations:
    print(reg.user.name)  # Новый запрос на каждой итерации!
```
Транзакции
```python
# ✅ ОБЯЗАТЕЛЬНО для критичных операций
from django.db import transaction

@transaction.atomic
def register_user_for_game(user, game):
    # Блокировка строки
    game = Game.objects.select_for_update().get(id=game.id)
    
    # Проверки
    if game.registrations.filter(is_active=True).count() >= game.main_limit:
        ...
    
    # Изменения
    registration = GameRegistration.objects.create(...)
    
    return registration
```
---
🎯 Business Logic (Services)
Структура сервиса
```python
# registrations/services.py

class RegistrationService:
    """
    Сервис для работы с записями на игры.
    
    ВСЯ бизнес-логика ТОЛЬКО здесь!
    Views только вызывают методы сервиса.
    """
    
    @staticmethod
    def register_user(user: User, game: Game) -> GameRegistration:
        """
        Записывает пользователя на игру.
        
        ⚠️ КРИТИЧНО: Разделение транзакции и уведомлений!
        
        Args:
            user: Пользователь
            game: Игра
            
        Returns:
            Созданная запись
            
        Raises:
            ValidationError: если запись невозможна
        """
        # Шаг 1: Транзакция БД (быстро, без внешних вызовов)
        registration = RegistrationService._create_registration_in_transaction(
            user, game
        )
        
        # Шаг 2: Уведомления (ПОСЛЕ commit, через Celery)
        # ✅ ПРАВИЛЬНО: Email вне транзакции
        send_registration_confirmation_task.delay(registration.id)
        
        return registration
    
    @staticmethod
    @transaction.atomic
    def _create_registration_in_transaction(user: User, game: Game) -> GameRegistration:
        """
        Критическая секция: ТОЛЬКО операции с БД!
        
        ❌ ЗАПРЕЩЕНО внутри:
        - send_mail() - может зависнуть
        - HTTP запросы
        - file I/O
        - любые медленные операции
        
        ✅ РАЗРЕШЕНО:
        - SELECT, INSERT, UPDATE
        - Валидация данных
        - Бизнес-логика на Python
        """
        # 1. Валидация
        RegistrationService._validate_registration(user, game)
        
        # 2. Блокировка игры (защита от race condition)
        game = Game.objects.select_for_update().get(id=game.id)
        
        # 3. Определение статуса
        status = RegistrationService._determine_status(game)
        
        # 4. Создание записи
        registration = GameRegistration.objects.create(
            user=user,
            game=game,
            status=status,
            source='player',
            queue_position=0  # Будет пересчитано в rebuild_queue
        )
        
        # 5. Событие (это БД, допустимо)
        RegistrationEvent.objects.create(
            registration=registration,
            event_type='created',
            new_status=status,
            performed_by_user=user
        )
        
        # 6. Пересборка очереди (обязательно!)
        rebuild_queue(game.id)
        
        # ✅ Транзакция завершается ЗДЕСЬ
        return registration
        
        # ❌ НЕ отправляем email здесь!
        # Email отправится через Celery ПОСЛЕ commit
    
    @staticmethod
    def _validate_registration(user, game):
        """Private метод валидации"""
        if not user.is_active:
            raise ValidationError("User not active")
        
        if GameRegistration.objects.filter(
            user=user, game=game, is_active=True
        ).exists():
            raise ValidationError("Already registered")
    
    @staticmethod
    def _determine_status(game):
        """Private метод определения статуса"""
        count = game.registrations.filter(
            status='main', is_active=True
        ).count()
        
        return 'main' if count < game.main_limit else 'reserve'
```
Правила для сервисов:
```python
✅ По умолчанию: статические методы (@staticmethod)
   - Простота использования
   - Не нужен instance
   - Подходит для 90% случаев

⚠️ Допускается instance/class при:
   - Нужны моки для тестов
   - Dependency Injection
   - Сложная композиция сервисов
   - Shared state между методами

✅ Public методы документированы (docstring обязателен)
✅ Private методы с _ префиксом
✅ Транзакции для критичных операций
✅ Валидация ПЕРЕД изменением данных
✅ Создание событий (RegistrationEvent)
✅ Уведомления через Celery ПОСЛЕ транзакции (не внутри!)
```
Пример с instance (когда нужны моки):
```python
class RegistrationService:
    def __init__(self, email_service=None, audit_service=None):
        """
        Dependency Injection для тестирования
        """
        self.email_service = email_service or EmailService()
        self.audit_service = audit_service or AuditService()
    
    def register_user(self, user, game):
        """Теперь можно замокать email_service в тестах"""
        registration = self._create_in_transaction(user, game)
        
        # Email через инжектированный сервис
        self.email_service.send_confirmation(registration)
        
        return registration

# В тестах:
def test_register_user():
    mock_email = MagicMock()
    service = RegistrationService(email_service=mock_email)
    
    service.register_user(user, game)
    
    mock_email.send_confirmation.assert_called_once()
```
Правило выбора:
```
Простой сервис (CRUD, queries) → @staticmethod
Сложный сервис (внешние API, моки) → instance methods
```
---
🎨 Views
```python
# ✅ ПРАВИЛЬНО: тонкие views, логика в сервисах

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

@login_required
def register_for_game_view(request, game_id):
    """Запись на игру"""
    game = get_object_or_404(Game, id=game_id)
    
    if request.method == 'POST':
        try:
            # ✅ Логика в сервисе
            registration = RegistrationService.register_user(
                user=request.user,
                game=game
            )
            
            messages.success(request, f'Вы записаны: {registration.status}')
            return redirect('game_detail', game_id=game.id)
            
        except ValidationError as e:
            messages.error(request, str(e))
    
    return render(request, 'games/register.html', {'game': game})
```
```python
# ❌ НЕПРАВИЛЬНО: логика в view

@login_required
def register_for_game_view(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    
    # ❌ Вся логика прямо здесь!
    if GameRegistration.objects.filter(user=request.user, game=game).exists():
        messages.error(request, 'Already registered')
        return redirect('game_detail', game_id=game.id)
    
    count = game.registrations.filter(status='main').count()
    status = 'main' if count < 18 else 'reserve'
    
    registration = GameRegistration.objects.create(
        user=request.user,
        game=game,
        status=status
    )
    ...
```
---
📝 Forms
```python
# ✅ ПРАВИЛЬНО: используем Django Forms

from django import forms

class GameCreateForm(forms.ModelForm):
    """Форма создания игры"""
    
    class Meta:
        model = Game
        fields = [
            'game_date',
            'start_time',
            'location_name',
            'main_limit',
            'description'
        ]
        widgets = {
            'game_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def clean_game_date(self):
        """Валидация: дата не в прошлом"""
        date = self.cleaned_data['game_date']
        if date < timezone.now().date():
            raise ValidationError("Дата не может быть в прошлом")
        return date
```
---
---
🔄 Queue Management (КРИТИЧНО!)
🔥 rebuild_queue() - ЕДИНСТВЕННЫЙ источник истины
ПРАВИЛО: После ЛЮБОГО изменения состава → rebuild_queue()
⚠️ ВАЖНО: Транзакционные границы
```python
# rebuild_queue() имеет ДВА варианта использования:

# 1️⃣ Внутри существующей транзакции (предпочтительно)
def rebuild_queue_internal(game_id: int) -> None:
    """
    Вызывается ВНУТРИ @transaction.atomic
    
    НЕ открывает свою транзакцию.
    НЕ делает select_for_update (уже сделано выше по стеку).
    
    Использование:
    @transaction.atomic
    def some_operation():
        game = Game.objects.select_for_update().get(id=game_id)
        # ... изменения
        rebuild_queue_internal(game_id)  # ✅ Внутри той же транзакции
    """
    # Без transaction.atomic здесь!
    # Без select_for_update здесь!
    
    game = Game.objects.get(id=game_id)  # Уже залочена выше
    
    registrations = list(
        game.registrations.filter(
            is_active=True
        ).exclude(
            status='cancelled'
        ).order_by('registered_at')
    )
    
    # Присваиваем позиции и статусы
    for i, reg in enumerate(registrations, start=1):
        reg.queue_position = i
        old_status = reg.status
        
        if i <= game.main_limit:
            reg.status = 'main'
        else:
            reg.status = 'reserve'
        
        reg.save(update_fields=['queue_position', 'status'])
        
        # Логируем изменения
        if old_status != reg.status:
            RegistrationEvent.objects.create(
                registration=reg,
                event_type='status_changed_by_rebuild',
                old_status=old_status,
                new_status=reg.status,
                performed_by_system=True
            )


# 2️⃣ Автономный вызов (standalone)
def rebuild_queue_standalone(game_id: int) -> None:
    """
    Вызывается СНАРУЖИ, сам открывает транзакцию.
    
    Использование:
    - Celery tasks
    - Management commands
    - Admin actions
    - Когда нет внешней транзакции
    """
    with transaction.atomic():
        # ✅ Блокируем игру
        game = Game.objects.select_for_update().get(id=game_id)
        
        # ✅ Вызываем внутренний метод
        rebuild_queue_internal(game_id)


# 🎯 ПРАВИЛО ИСПОЛЬЗОВАНИЯ:
"""
✅ ВНУТРИ @transaction.atomic:
   → rebuild_queue_internal(game_id)
   
✅ СНАРУЖИ (Celery, admin):
   → rebuild_queue_standalone(game_id)
   
❌ НЕ ДЕЛАТЬ:
   with transaction.atomic():
       ...
       rebuild_queue_standalone(game_id)  # ❌ Вложенная транзакция!
"""
```
Примеры правильного использования:
```python
# ✅ ПРАВИЛЬНО: Внутри транзакции
@transaction.atomic
def register_user_internal(user, game):
    """Вызывается из view/API"""
    game = Game.objects.select_for_update().get(id=game.id)
    
    registration = GameRegistration.objects.create(...)
    
    # ✅ Внутренний метод (без своей транзакции)
    rebuild_queue_internal(game.id)
    
    return registration


# ✅ ПРАВИЛЬНО: Автономный вызов
@shared_task
def rebuild_queue_task(game_id):
    """Celery task для пересборки"""
    # ✅ Standalone метод (сам откроет транзакцию)
    rebuild_queue_standalone(game_id)


# ✅ ПРАВИЛЬНО: Admin action
@admin.action(description='Пересобрать очередь')
def admin_rebuild_queue(modeladmin, request, queryset):
    """Массовая пересборка для выбранных игр"""
    for game in queryset:
        # ✅ Standalone метод
        rebuild_queue_standalone(game.id)
```
ПРАВИЛО:
```
✅ rebuild_queue_internal() - внутри существующей транзакции
✅ rebuild_queue_standalone() - автономный вызов
❌ НЕ путать границы транзакций
❌ НЕ вкладывать транзакции друг в друга
```
Альтернатива (если хочется один метод):
```python
def rebuild_queue(game_id: int, already_locked: bool = False) -> None:
    """
    Универсальный метод с флагом.
    
    Args:
        game_id: ID игры
        already_locked: True если Game уже залочена в текущей транзакции
    """
    if already_locked:
        # Внутри транзакции
        game = Game.objects.get(id=game_id)
    else:
        # Автономный вызов
        with transaction.atomic():
            game = Game.objects.select_for_update().get(id=game_id)
    
    # Дальше общая логика...
    
# Использование:
@transaction.atomic
def some_func():
    game = Game.objects.select_for_update().get(...)
    rebuild_queue(game.id, already_locked=True)  # ✅ Явно

rebuild_queue(game_id, already_locked=False)  # ✅ Автономно
```
---
🔐 Security
CSRF Protection
```python
# ✅ ВСЕГДА используем {% csrf_token %}
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Submit</button>
</form>
```
SQL Injection
```python
# ✅ ПРАВИЛЬНО: Django ORM
users = User.objects.filter(email=email)

# ❌ НЕПРАВИЛЬНО: raw SQL
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
```
XSS Protection
```python
# ✅ Django автоматически экранирует
<p>{{ user.name }}</p>

# ❌ ОПАСНО: |safe только для доверенного контента
<p>{{ user.comment|safe }}</p>
```
🔥 КРИТИЧНО: Rate Limiting
Проблема: Пн 00:01 - 50 человек жмут "Записаться"
Решение: Многоуровневая защита
```python
# Уровень 1: Django-ratelimit (middleware)
from django_ratelimit.decorators import ratelimit

@ratelimit(
    key='user',      # По пользователю
    rate='5/m',      # 5 запросов в минуту
    method='POST',   # Только POST
    block=True       # Блокировать при превышении
)
def register_for_game_view(request, game_id):
    """
    Rate limit предотвращает:
    - Случайные двойные клики
    - Преднамеренный спам
    - DoS атаки
    """
    ...

# Уровень 2: Cache-based lock (per user+game)
from django.core.cache import cache

def register_with_lock(user_id, game_id):
    """
    Оптимистичная блокировка через Redis
    """
    lock_key = f'registration_lock_{user_id}_{game_id}'
    
    # ✅ Попытка взять lock
    if not cache.add(lock_key, True, timeout=10):
        raise ValidationError("Запись уже обрабатывается, подождите")
    
    try:
        # Выполняем запись
        return register_user_for_game(user_id, game_id)
    finally:
        # ✅ Освобождаем lock
        cache.delete(lock_key)

# Уровень 3: Frontend debounce
# В JavaScript (если используете)
let isSubmitting = false;

button.addEventListener('click', async (e) => {
    if (isSubmitting) return;  // ✅ Игнорируем повторные клики
    
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
Настройка django-ratelimit:
```python
# settings.py
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'  # Используем Redis

# Разные лимиты для разных действий
REGISTRATION_RATE_LIMIT = '5/m'   # Запись на игру
LOGIN_RATE_LIMIT = '10/h'          # Вход
API_RATE_LIMIT = '100/h'           # API запросы
```
ПРАВИЛО:
```
❌ Полагаться только на frontend защиту
✅ БД constraint + select_for_update
✅ Backend rate limiting
✅ Cache lock
✅ Frontend debounce (дополнительно)
```
---
✉️ Email / Notifications
🔥 КРИТИЧНО: Транзакции и внешние вызовы
ПРАВИЛО: Никаких внешних операций внутри транзакций!
```python
# ❌ ОПАСНО: Email внутри транзакции
@transaction.atomic
def register_user(user, game):
    registration = GameRegistration.objects.create(...)
    
    # ❌ Email может зависнуть на 30 секунд!
    # ❌ Транзакция держит lock всё это время!
    # ❌ Другие пользователи не могут записаться!
    send_mail(...)  
    
    return registration
```
```python
# ✅ ПРАВИЛЬНО: transaction.on_commit (РЕКОМЕНДУЕТСЯ!)

@transaction.atomic
def register_user(user, game):
    """
    Использование transaction.on_commit гарантирует:
    1. Task запустится ТОЛЬКО после успешного commit
    2. Если транзакция откатится - task НЕ запустится
    3. Не нужен отдельный метод _create_registration
    """
    game = Game.objects.select_for_update().get(id=game.id)
    
    registration = GameRegistration.objects.create(
        user=user,
        game=game,
        ...
    )
    
    rebuild_queue_internal(game.id)
    
    # ✅ КРИТИЧНО: on_commit запустит task ПОСЛЕ commit
    transaction.on_commit(
        lambda: send_registration_email.delay(registration.id)
    )
    
    return registration

# Альтернатива: хелпер для on_commit
def send_email_after_commit(task, *args, **kwargs):
    """Обёртка для запуска Celery task после commit"""
    transaction.on_commit(
        lambda: task.delay(*args, **kwargs)
    )

# Использование:
@transaction.atomic
def register_user(user, game):
    registration = GameRegistration.objects.create(...)
    rebuild_queue_internal(game.id)
    
    # ✅ Читаемо и безопасно
    send_email_after_commit(
        send_registration_email,
        registration.id
    )
    
    return registration
```
Почему on_commit лучше чем просто Celery после функции:
```python
# ⚠️ ПРОБЛЕМА: Task может запуститься ДО commit
def register_user(user, game):
    registration = _create_in_transaction(user, game)  # commit здесь
    
    # ⚠️ Task запустился
    send_email.delay(registration.id)
    
    # Но если _create_in_transaction откатится?
    # Task уже в очереди! ❌

# ✅ РЕШЕНИЕ: on_commit
@transaction.atomic
def register_user(user, game):
    registration = GameRegistration.objects.create(...)
    
    transaction.on_commit(
        lambda: send_email.delay(registration.id)
    )
    # ✅ Task запустится ТОЛЬКО после commit
    # ✅ Если rollback - task НЕ запустится
```
ПРАВИЛО:
```
✅ ВСЕГДА: transaction.on_commit() для Celery tasks
✅ ВСЕГДА: on_commit для любых действий "после успешной транзакции"
❌ НИКОГДА: внешние вызовы внутри @transaction.atomic
```
Что НЕЛЬЗЯ внутри @transaction.atomic:
```python
❌ send_mail() - может зависнуть
❌ requests.get() - HTTP запросы
❌ open() / write() - файловые операции
❌ time.sleep() - задержки
❌ любые медленные операции
```
Что МОЖНО внутри @transaction.atomic:
```python
✅ SELECT, INSERT, UPDATE, DELETE
✅ Валидация данных
✅ Бизнес-логика на Python
✅ Вызов других методов БД
```
---
🔥 КРИТИЧНО: Idempotency Celery задач
ПРАВИЛО: Все задачи ДОЛЖНЫ быть идемпотентными!
```python
# ❌ ОПАСНО: Не идемпотентная задача
@shared_task
def send_registration_open_email(game_id):
    """
    Проблема:
    1. Task выполнился
    2. Email отправлен
    3. Task упал на последней строке
    4. Celery retry
    5. Email отправлен СНОВА ❌
    """
    game = Game.objects.get(id=game_id)
    users = User.objects.filter(is_active=True)
    
    for user in users:
        send_mail(...)  # Каждый раз заново!
```
```python
# ✅ ПРАВИЛЬНО: Идемпотентная задача

@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(SMTPException,)
)
def send_registration_open_email(self, game_id):
    """
    Можно вызвать сколько угодно раз безопасно!
    
    Проверяет: уже выполнено?
    Если да → пропускает
    Если нет → выполняет и помечает
    """
    game = Game.objects.get(id=game_id)
    
    # ✅ Проверка идемпотентности
    if game.registration_open_email_sent:
        logger.info(f"Email already sent for game {game_id}, skipping")
        return {'status': 'already_sent'}
    
    # Отправка
    users = User.objects.filter(is_active=True)
    sent_count = 0
    
    for user in users:
        try:
            send_mail(...)
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {user.id}: {e}")
    
    # ✅ Пометка выполнения (АТОМАРНО!)
    Game.objects.filter(id=game_id).update(
        registration_open_email_sent=True
    )
    
    return {
        'status': 'sent',
        'count': sent_count
    }
```
Флаги идемпотентности (добавить в модели):
```python
class Game(models.Model):
    # ... другие поля
    
    # Флаги выполнения задач (для идемпотентности)
    registration_open_email_sent = models.BooleanField(default=False)
    reminder_tuesday_sent = models.BooleanField(default=False)
    reminder_game_day_sent = models.BooleanField(default=False)
    registration_closed_processed = models.BooleanField(default=False)
```
Альтернатива: проверка через состояние
```python
@shared_task
def promote_from_reserve_task(game_id):
    """
    Идемпотентность через проверку текущего состояния.
    
    Не нужен флаг, просто проверяем:
    - Есть места в основе?
    - Есть резервисты?
    
    Если нет → ничего не делаем (безопасно)
    """
    with transaction.atomic():
        game = Game.objects.select_for_update().get(id=game_id)
        
        main_count = game.registrations.filter(
            status='main', is_active=True
        ).count()
        
        # ✅ Проверка: нужно ли действие?
        if main_count >= game.main_limit:
            return {'status': 'no_space'}
        
        reserve = game.registrations.filter(
            status='reserve', is_active=True
        ).order_by('queue_position').first()
        
        if not reserve:
            return {'status': 'no_reserves'}
        
        # Продвижение (идемпотентное действие)
        reserve.status = 'main'
        reserve.save()
        
        rebuild_queue(game_id)
    
    # Email вне транзакции
    send_promoted_email.delay(reserve.id)
    
    return {'status': 'promoted', 'user_id': reserve.user_id}
```
Тестирование идемпотентности:
```python
def test_task_idempotency():
    """Задача безопасна при двойном вызове"""
    game = Game.objects.create(...)
    
    # Первый вызов
    result1 = send_registration_open_email(game.id)
    assert result1['status'] == 'sent'
    
    # Второй вызов (симуляция retry)
    result2 = send_registration_open_email(game.id)
    assert result2['status'] == 'already_sent'
    
    # ✅ Email отправлен только раз
```
---
Celery: асинхронно через Celery
Правильная структура:
from celery import shared_task
@shared_task
def send_registration_open_email(game_id):
"""Отправка email об открытии записи"""
game = Game.objects.get(id=game_id)
users = User.objects.filter(is_active=True, approval_status='approved')
    for user in users:
        send_mail(
            subject=f'Запись на игру {game.game_date}',
            message=render_to_string('emails/registration_open.txt', {
                'user': user,
                'game': game
            }),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        
        # ✅ Логируем отправку
        Notification.objects.create(
            user=user,
            type='registration_open',
            status='sent',
            related_game=game
        )
```

---

## 🧪 Testing

```python
# ✅ ПРАВИЛЬНО: тесты для сервисов

import pytest
from django.contrib.auth import get_user_model
from registrations.services import RegistrationService

User = get_user_model()

@pytest.mark.django_db
class TestRegistrationService:
    """Тесты сервиса записи"""
    
    def test_register_user_to_main(self):
        """Тест записи в основу"""
        # Arrange
        user = User.objects.create(email='test@example.com')
        game = Game.objects.create(
            game_date='2025-04-01',
            main_limit=18
        )
        
        # Act
        registration = RegistrationService.register_user(user, game)
        
        # Assert
        assert registration.status == 'main'
        assert registration.user == user
        assert registration.game == game
    
    def test_register_user_to_reserve_when_main_full(self):
        """Тест записи в резерв когда основа полна"""
        # ... similar test
```
---
📦 Dependencies Management
```python
# requirements.txt
# ✅ Закрепляем версии

Django==5.0.1
psycopg2-binary==2.9.9
celery==5.3.4
redis==5.0.1

# ❌ НЕ используем latest
Django
celery
```
---
🚀 Deployment
Environment Variables
```python
# ✅ НИКОГДА не коммитим секреты

# settings/base.py
SECRET_KEY = os.environ.get('SECRET_KEY')
DATABASE_URL = os.environ.get('DATABASE_URL')

# .env.example (коммитим)
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://...

# .env (НЕ коммитим, в .gitignore)
SECRET_KEY=actual-secret-key
DATABASE_URL=postgresql://real-credentials
```
---
📚 Documentation
```python
# ✅ ОБЯЗАТЕЛЬНО: docstrings

def rebuild_queue(game: Game) -> None:
    """
    Пересобирает очередь записи на игру.
    
    КРИТИЧЕСКАЯ ФУНКЦИЯ!
    Вызывается после любого изменения состава.
    
    Алгоритм:
    1. Берёт все активные записи
    2. Сортирует по registered_at
    3. Присваивает queue_position
    4. Первые N → main, остальные → reserve
    
    Args:
        game: Объект игры
        
    Returns:
        None
        
    Side effects:
        - Обновляет status всех регистраций
        - Создаёт RegistrationEvent для изменённых
    """
    ...
```
---
⚠️ Common Pitfalls (Частые ошибки)
1. Race Conditions
```python
# ❌ ОПАСНО
if game.registrations.count() < 18:
    # Между проверкой и созданием другой запрос может влезть!
    GameRegistration.objects.create(...)

# ✅ ПРАВИЛЬНО
@transaction.atomic
def register():
    game = Game.objects.select_for_update().get(id=game_id)
    if game.registrations.count() < 18:
        GameRegistration.objects.create(...)
```
2. N+1 Queries
```python
# ❌ ОПАСНО
registrations = GameRegistration.objects.all()
for reg in registrations:
    print(reg.user.name)  # Запрос на каждой итерации!

# ✅ ПРАВИЛЬНО
registrations = GameRegistration.objects.select_related('user').all()
for reg in registrations:
    print(reg.user.name)  # Один запрос
```
3. Timezone Issues
```python
# ❌ ОПАСНО
from datetime import datetime
now = datetime.now()  # Локальная таймзона!

# ✅ ПРАВИЛЬНО
from django.utils import timezone
now = timezone.now()  # UTC
```
---
✅ Pre-commit Checklist
Перед каждым коммитом:
```
✅ Код проходит flake8/black
✅ Все тесты зелёные
✅ Нет хардкоженных секретов
✅ Docstrings для новых функций
✅ Migrations созданы (если менял модели)
✅ .env.example обновлён (если новые переменные)
```
---
🎯 AI-specific Guidelines
Для Claude:
```
✅ Генерируй полные файлы (не обрезай)
✅ Используй Artifacts для кода
✅ Следуй этим правилам строго
✅ Docstrings обязательны
```
Для ChatGPT:
```
✅ При review проверяй соответствие этим правилам
✅ Указывай на нарушения явно
✅ Предлагай рефакторинг
```
Для Cursor:
```
✅ @codebase читай этот файл перед генерацией
✅ Следуй naming conventions
✅ Не генерируй код нарушающий эти правила
```
---
Эти правила не рекомендации, а ТРЕБОВАНИЯ!
Любой код, нарушающий их, должен быть отклонён на code review.
---
🟡 Дополнительные улучшения (не критично для MVP)
1. Logging Structure
Добавить уровни логирования:
```python
import logging

logger = logging.getLogger(__name__)

# ✅ ПРАВИЛЬНО: Разные уровни для разных ситуаций
def register_user(user, game):
    logger.info(f"User {user.id} attempting registration for game {game.id}")
    
    try:
        registration = _create_in_transaction(user, game)
        logger.info(f"Registration {registration.id} created successfully")
        return registration
        
    except ValidationError as e:
        logger.warning(f"Registration failed for user {user.id}: {e}")
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in registration: {e}", exc_info=True)
        raise

# Уровни:
# DEBUG   - детальная отладочная информация
# INFO    - обычные события (создание записи)
# WARNING - что-то странное, но не критично
# ERROR   - ошибки, которые нужно исправить
# CRITICAL - система не работает
```
Structured logging (опционально):
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "registration_created",
    user_id=user.id,
    game_id=game.id,
    status=registration.status,
    queue_position=registration.queue_position
)
# Легко парсить и анализировать
```
---
2. Pagination
Для больших списков:
```python
from django.core.paginator import Paginator

def game_comments_view(request, game_id):
    """Комментарии с пагинацией"""
    game = get_object_or_404(Game, id=game_id)
    comments = game.comments.filter(is_visible=True).order_by('-created_at')
    
    # ✅ Пагинация (20 на страницу)
    paginator = Paginator(comments, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'comments.html', {
        'game': game,
        'comments': page_obj  # Не comments!
    })

# В template:
# {% for comment in comments %}
#   ...
# {% endfor %}
# 
# <div class="pagination">
#   {% if comments.has_previous %}
#     <a href="?page={{ comments.previous_page_number }}">« Предыдущая</a>
#   {% endif %}
#   
#   Страница {{ comments.number }} из {{ comments.paginator.num_pages }}
#   
#   {% if comments.has_next %}
#     <a href="?page={{ comments.next_page_number }}">Следующая »</a>
#   {% endif %}
# </div>
```
---
3. Soft Delete Policy
Чёткие правила что удалять:
🎯 Soft Delete Policy для моделей проекта:
Модель	Политика	Причина	Retention
GameRegistration	✅ Soft Delete	Статистика, рейтинг	Навсегда
Comment	✅ Soft Delete	Аудит, контекст	Навсегда
Announcement	✅ Soft Delete	История объявлений	Навсегда
User	✅ Soft Delete	GDPR, аудит	Навсегда*
Game	❌ Hard Delete	Нет необходимости	N/A
RegistrationEvent	🔄 Retention	Технические логи	12 месяцев
Notification	🔄 Retention	Старые уведомления	90 дней
AuditLog	🔄 Retention	Админ действия	24 месяца
*GDPR: User можно анонимизировать вместо удаления
Реализация:
```python
# ✅ Soft delete модели
class GameRegistration(models.Model):
    # ... поля
    is_active = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User, 
        null=True, 
        on_delete=models.SET_NULL,
        related_name='deleted_registrations'
    )
    
    objects = SoftDeleteManager()  # Только активные
    all_objects = models.Manager()  # Все
    
    def soft_delete(self, deleted_by=None):
        """Мягкое удаление"""
        self.is_active = False
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.save(update_fields=['is_active', 'deleted_at', 'deleted_by'])
    
    def restore(self):
        """Восстановление"""
        self.is_active = True
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_active', 'deleted_at', 'deleted_by'])


# ❌ Hard delete модели
class Game(models.Model):
    # Обычная модель, удаляется через .delete()
    pass


# 🔄 Retention модели
class Notification(models.Model):
    # ... поля
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['created_at']),  # Для cleanup
        ]

# Management command для cleanup
# python manage.py cleanup_old_notifications
class Command(BaseCommand):
    """Удаление старых уведомлений (>90 дней)"""
    
    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=90)
        
        deleted, _ = Notification.objects.filter(
            created_at__lt=cutoff,
            status__in=['sent', 'failed']  # Не удаляем pending
        ).delete()
        
        self.stdout.write(f'Deleted {deleted} old notifications')
```
Cron для retention:
```python
# В Celery Beat
@shared_task
def cleanup_old_data():
    """Еженедельная очистка старых данных"""
    from django.core.management import call_command
    
    # Notifications: >90 дней
    call_command('cleanup_old_notifications')
    
    # RegistrationEvent: >12 месяцев
    call_command('cleanup_old_events')
    
    # AuditLog: >24 месяца
    call_command('cleanup_old_audit_logs')

# settings.py - Celery Beat schedule
CELERY_BEAT_SCHEDULE = {
    'cleanup-old-data': {
        'task': 'core.tasks.cleanup_old_data',
        'schedule': crontab(day_of_week=0, hour=3, minute=0),  # Воскресенье 03:00
    },
}
```
GDPR - анонимизация вместо удаления:
```python
class User(models.Model):
    # ...
    is_anonymized = models.BooleanField(default=False)
    
    def anonymize(self):
        """GDPR-compliant удаление"""
        self.email = f'deleted_{self.id}@anonymized.local'
        self.first_name = 'Deleted'
        self.last_name = 'User'
        self.phone = ''
        self.is_active = False
        self.is_anonymized = True
        self.save()
        
        # Статистика сохраняется, но без личных данных
        # GameRegistration остаётся с user_id, но User анонимизирован
```
ПРАВИЛО:
```
✅ Soft Delete: когда нужна статистика/аудит
✅ Hard Delete: когда данные не нужны
✅ Retention: автоматическое удаление старых данных
✅ GDPR: анонимизация вместо удаления пользователей
```
---
4. Batch Operations (для администраторов)
```python
# Admin action для массовых операций
@admin.action(description='Одобрить выбранных пользователей')
def approve_users_batch(modeladmin, request, queryset):
    """Массовое одобрение"""
    count = queryset.filter(approval_status='pending').update(
        approval_status='approved',
        approved_at=timezone.now(),
        approved_by=request.user
    )
    
    modeladmin.message_user(
        request,
        f'Одобрено пользователей: {count}'
    )
```
---
5. Caching (опционально)
```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page

# Кешируем медленные запросы
def get_game_statistics(game_id):
    """Статистика игры (кешируется на 5 минут)"""
    cache_key = f'game_stats_{game_id}'
    
    stats = cache.get(cache_key)
    if stats is not None:
        return stats
    
    # Медленный запрос
    stats = {
        'total_registered': ...,
        'main_count': ...,
        'reserve_count': ...,
        'attendance_rate': ...
    }
    
    cache.set(cache_key, stats, timeout=300)  # 5 минут
    return stats

# Инвалидация кеша при изменении
def register_user(user, game):
    registration = _create_in_transaction(user, game)
    
    # ✅ Сбрасываем кеш
    cache.delete(f'game_stats_{game.id}')
    
    return registration
```
---
ПРАВИЛО для улучшений:
```
✅ Реализовывать ТОЛЬКО если действительно нужно
❌ Не добавлять "на всякий случай"
✅ MVP сначала, оптимизация потом
```

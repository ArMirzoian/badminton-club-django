"""
Registration Services - вся бизнес-логика
Следует engineering_rules.md

КРИТИЧНО:
- rebuild_queue() - ЕДИНСТВЕННЫЙ источник истины для queue_position и status
- transaction.on_commit() для email
- Все изменения через эти сервисы
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import GameRegistration, RegistrationEvent


def rebuild_queue_internal(game_id: int) -> None:
    """
    Пересборка очереди ВНУТРИ существующей транзакции.
    
    НЕ открывает свою транзакцию.
    НЕ делает select_for_update (уже сделано выше).
    
    Использование:
    @transaction.atomic
    def some_operation():
        game = Game.objects.select_for_update().get(id=game_id)
        # ... изменения
        rebuild_queue_internal(game_id)
    """
    from apps.games.models import Game
    
    game = Game.objects.get(id=game_id)
    
    # Все активные записи (кроме отменённых), сортировка
    registrations = list(
        game.registrations.filter(
            is_active=True
        ).exclude(
            status='cancelled'
        ).order_by(
            '-admin_priority',  # Админ приоритет первым
            'registered_at'      # Потом по времени
        )
    )
    
    # Присваиваем позиции и статусы
    for i, reg in enumerate(registrations, start=1):
        reg.queue_position = i
        old_status = reg.status
        
        # Определяем статус
        if i <= game.main_limit:
            reg.status = 'main'
        else:
            reg.status = 'reserve'
        
        reg.save(update_fields=['queue_position', 'status'])
        
        # Логируем изменение статуса
        if old_status != reg.status:
            RegistrationEvent.objects.create(
                registration=reg,
                event_type='status_changed_by_rebuild',
                old_status=old_status,
                new_status=reg.status,
                performed_by_system=True
            )


def rebuild_queue_standalone(game_id: int) -> None:
    """
    Автономный вызов rebuild_queue.
    Сам открывает транзакцию и блокировку.
    
    Использование:
    - Celery tasks
    - Management commands
    - Admin actions
    """
    from apps.games.models import Game
    
    with transaction.atomic():
        game = Game.objects.select_for_update().get(id=game_id)
        rebuild_queue_internal(game_id)


@transaction.atomic
def register_user_for_game(user, game):
    """
    Запись пользователя на игру.
    
    КРИТИЧНО:
    - transaction.atomic + select_for_update
    - Проверка дубля
    - rebuild_queue_internal в той же транзакции
    - Email через transaction.on_commit (не внутри транзакции!)
    """
    from apps.games.models import Game
    
    # Блокировка игры
    game = Game.objects.select_for_update().get(id=game.id)
    
    # Проверка: запись открыта?
    if not game.is_open:
        raise ValidationError("Запись закрыта")
    
    # Проверка: дубль?
    if GameRegistration.objects.filter(
        user=user,
        game=game,
        is_active=True
    ).exists():
        raise ValidationError("Вы уже записаны на эту игру")
    
    # Определение статуса
    main_count = game.registrations.filter(
        status='main',
        is_active=True
    ).count()
    
    initial_status = 'main' if main_count < game.main_limit else 'reserve'
    
    # Создание записи
    registration = GameRegistration.objects.create(
        user=user,
        game=game,
        status=initial_status,
        source='player'
    )
    
    # Событие
    RegistrationEvent.objects.create(
        registration=registration,
        event_type='created',
        new_status=initial_status,
        performed_by_user=user
    )
    
    # Пересборка очереди
    rebuild_queue_internal(game.id)
    
    # Email ПОСЛЕ commit через Celery (создадим позже)
    # transaction.on_commit(
    #     lambda: send_registration_email.delay(registration.id)
    # )
    
    return registration


@transaction.atomic
def cancel_registration(registration, cancelled_by=None):
    """
    Отмена записи.
    
    КРИТИЧНО:
    - Если был в основе → продвижение из резерва
    - Email через on_commit
    """
    from apps.games.models import Game
    
    game = Game.objects.select_for_update().get(id=registration.game_id)
    
    was_in_main = registration.status == 'main'
    
    # Отмена
    registration.status = 'cancelled'
    registration.is_active = False
    registration.deleted_at = timezone.now()
    registration.save(update_fields=['status', 'is_active', 'deleted_at'])
    
    # Событие
    RegistrationEvent.objects.create(
        registration=registration,
        event_type='cancelled',
        old_status='main' if was_in_main else 'reserve',
        new_status='cancelled',
        performed_by_user=cancelled_by
    )
    
    # Пересборка (автоматически поднимет из резерва если нужно)
    rebuild_queue_internal(game.id)
    
    # Email тому кто поднялся (через Celery, создадим позже)
    # if was_in_main:
    #     transaction.on_commit(
    #         lambda: notify_promoted_from_reserve.delay(game.id)
    #     )
    
    return registration


@transaction.atomic
def admin_override_to_main(admin_user, registration):
    """
    Админ переводит в основу вне очереди.
    
    КРИТИЧНО:
    - Через admin_priority флаг
    - Через rebuild_queue (не вручную!)
    - Логируется в AuditLog
    """
    from apps.games.models import Game
    
    game = Game.objects.select_for_update().get(id=registration.game_id)
    
    # Установка приоритета
    registration.admin_priority = True
    registration.save(update_fields=['admin_priority'])
    
    # Пересборка (учтёт admin_priority)
    rebuild_queue_internal(game.id)
    
    # Событие
    RegistrationEvent.objects.create(
        registration=registration,
        event_type='admin_override',
        new_status=registration.status,  # Уже установлен rebuild_queue
        performed_by_user=admin_user
    )
    
    return registration

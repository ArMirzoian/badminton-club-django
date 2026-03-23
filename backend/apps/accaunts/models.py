"""
User модель - следует engineering_rules.md
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Кастомная модель пользователя для бадминтон клуба.
    
    Расширяет стандартную Django User модель полями:
    - telegram_id: ID из Telegram бота (для миграции)
    - display_name: Отображаемое имя (🔷Артур М.)
    - approval_status: Статус одобрения (pending/approved/rejected)
    - role: Роль (player/admin)
    """
    
    # Choices
    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Ожидает одобрения'),
        ('approved', 'Одобрен'),
        ('rejected', 'Отклонён'),
    ]
    
    ROLE_CHOICES = [
        ('player', 'Игрок'),
        ('admin', 'Администратор'),
    ]
    
    # Дополнительные поля
    telegram_id = models.BigIntegerField(
        'Telegram ID',
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text='ID пользователя из Telegram бота'
    )
    
    display_name = models.CharField(
        'Отображаемое имя',
        max_length=100,
        help_text='Например: 🔷Артур М.'
    )
    
    approval_status = models.CharField(
        'Статус одобрения',
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    role = models.CharField(
        'Роль',
        max_length=20,
        choices=ROLE_CHOICES,
        default='player',
        db_index=True
    )
    
    approved_at = models.DateTimeField(
        'Дата одобрения',
        null=True,
        blank=True
    )
    
    approved_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_users',
        verbose_name='Одобрил'
    )
    
    # Soft delete
    is_active = models.BooleanField(
        'Активен',
        default=True,
        db_index=True
    )
    
    deleted_at = models.DateTimeField(
        'Дата удаления',
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['display_name']
        indexes = [
            models.Index(fields=['telegram_id']),
            models.Index(fields=['approval_status']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.display_name
    
    def soft_delete(self, deleted_by=None):
        """Мягкое удаление пользователя"""
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_active', 'deleted_at'])
    
    def is_admin_user(self):
        """Проверка является ли пользователь админом"""
        return self.role == 'admin' or self.is_superuser

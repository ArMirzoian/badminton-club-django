"""
Django Admin для User модели
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админка для кастомной User модели"""
    
    list_display = ['display_name', 'email', 'telegram_id', 'approval_status', 'role', 'is_active']
    list_filter = ['approval_status', 'role', 'is_active', 'is_staff']
    search_fields = ['display_name', 'email', 'telegram_id']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('telegram_id', 'display_name', 'approval_status', 'role', 'approved_at', 'approved_by')
        }),
        ('Удаление', {
            'fields': ('deleted_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['approved_at', 'deleted_at']
    
    actions = ['approve_users', 'reject_users']
    
    def approve_users(self, request, queryset):
        """Одобрить выбранных пользователей"""
        from django.utils import timezone
        
        count = queryset.filter(approval_status='pending').update(
            approval_status='approved',
            approved_at=timezone.now()
        )
        self.message_user(request, f'Одобрено пользователей: {count}')
    approve_users.short_description = 'Одобрить выбранных'
    
    def reject_users(self, request, queryset):
        """Отклонить выбранных пользователей"""
        count = queryset.filter(approval_status='pending').update(
            approval_status='rejected'
        )
        self.message_user(request, f'Отклонено пользователей: {count}')
    reject_users.short_description = 'Отклонить выбранных'

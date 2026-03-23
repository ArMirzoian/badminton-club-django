"""
Django Admin для Registration моделей
"""
from django.contrib import admin
from .models import GameRegistration, RegistrationEvent


class RegistrationEventInline(admin.TabularInline):
    """Inline для истории событий"""
    model = RegistrationEvent
    extra = 0
    readonly_fields = ['event_type', 'old_status', 'new_status', 'performed_by_user', 'performed_by_system', 'created_at']
    can_delete = False


@admin.register(GameRegistration)
class GameRegistrationAdmin(admin.ModelAdmin):
    """Админка для GameRegistration"""
    
    list_display = ['user', 'game', 'status', 'queue_position', 'source', 'registered_at', 'is_active']
    list_filter = ['status', 'source', 'is_active', 'game__game_date']
    search_fields = ['user__display_name', 'user__email']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'game', 'status', 'queue_position', 'source')
        }),
        ('Дополнительно', {
            'fields': ('admin_priority', 'is_active', 'deleted_at')
        }),
        ('Метаданные', {
            'fields': ('registered_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['registered_at', 'deleted_at', 'queue_position']
    inlines = [RegistrationEventInline]
    
    actions = ['cancel_registrations', 'move_to_main_admin']
    
    def cancel_registrations(self, request, queryset):
        """Отменить выбранные записи"""
        from .services import cancel_registration
        
        count = 0
        for registration in queryset.filter(is_active=True):
            try:
                cancel_registration(registration, cancelled_by=request.user)
                count += 1
            except Exception:
                pass
        
        self.message_user(request, f'Отменено записей: {count}')
    cancel_registrations.short_description = 'Отменить выбранные записи'
    
    def move_to_main_admin(self, request, queryset):
        """Переместить в основу (админ override)"""
        from .services import admin_override_to_main
        
        count = 0
        for registration in queryset.filter(is_active=True):
            try:
                admin_override_to_main(request.user, registration)
                count += 1
            except Exception:
                pass
        
        self.message_user(request, f'Перемещено в основу: {count}')
    move_to_main_admin.short_description = 'Переместить в основу (приоритет)'


@admin.register(RegistrationEvent)
class RegistrationEventAdmin(admin.ModelAdmin):
    """Админка для RegistrationEvent"""
    
    list_display = ['registration', 'event_type', 'old_status', 'new_status', 'performed_by_user', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['registration__user__display_name']
    
    readonly_fields = ['registration', 'event_type', 'old_status', 'new_status', 'performed_by_user', 'performed_by_system', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

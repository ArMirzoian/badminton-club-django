"""
Django Admin для Game модели
"""
from django.contrib import admin
from .models import Game


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """Админка для Game"""
    
    list_display = ['game_date', 'start_time', 'main_limit', 'is_open', 'main_count', 'reserve_count']
    list_filter = ['is_open', 'game_date']
    search_fields = ['location_name']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('game_date', 'start_time', 'location_name', 'location_address', 'main_limit')
        }),
        ('Управление записью', {
            'fields': ('registration_open_at', 'registration_close_at', 'is_open')
        }),
        ('Флаги идемпотентности', {
            'fields': (
                'registration_open_email_sent',
                'reminder_tuesday_sent',
                'reminder_game_day_sent',
                'registration_closed_processed'
            ),
            'classes': ('collapse',)
        }),
        ('Метаданные', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['rebuild_queue_action', 'open_registration', 'close_registration']
    
    def rebuild_queue_action(self, request, queryset):
        """Пересобрать очередь для выбранных игр"""
        from apps.registrations.services import rebuild_queue_standalone
        
        for game in queryset:
            rebuild_queue_standalone(game.id)
        
        self.message_user(request, f'Очередь пересобрана для {queryset.count()} игр')
    rebuild_queue_action.short_description = 'Пересобрать очередь'
    
    def open_registration(self, request, queryset):
        """Открыть запись"""
        count = queryset.update(is_open=True)
        self.message_user(request, f'Запись открыта для {count} игр')
    open_registration.short_description = 'Открыть запись'
    
    def close_registration(self, request, queryset):
        """Закрыть запись"""
        count = queryset.update(is_open=False)
        self.message_user(request, f'Запись закрыта для {count} игр')
    close_registration.short_description = 'Закрыть запись'

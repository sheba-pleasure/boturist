from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import TelegramUser, Request, RequestFile, RequestMessage, BotSettings

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'first_name', 'last_name', 'is_active', 
                   'requests_count', 'created_at', 'last_activity')
    list_filter = ('is_active', 'created_at', 'last_activity')
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name')
    readonly_fields = ('created_at', 'last_activity')
    ordering = ('-last_activity',)

    def requests_count(self, obj):
        return obj.requests.count()
    requests_count.short_description = 'Количество запросов'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            requests_count=Count('requests')
        )

class RequestFileInline(admin.TabularInline):
    model = RequestFile
    extra = 0
    readonly_fields = ('file_name', 'file_size', 'file_type', 'created_at')
    fields = ('file', 'file_name', 'file_size', 'file_type', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

class RequestMessageInline(admin.TabularInline):
    model = RequestMessage
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('text', 'is_from_user', 'created_at')
    ordering = ('created_at',)

@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_link', 'platform', 'status', 'created_at', 
                   'completed_at', 'files_count', 'messages_count')
    list_filter = ('status', 'platform', 'created_at')
    search_fields = ('query', 'user__username', 'user__telegram_id')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    inlines = [RequestFileInline, RequestMessageInline]
    ordering = ('-created_at',)

    def user_link(self, obj):
        url = reverse('admin:admin_panel_telegramuser_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user)
    user_link.short_description = 'Пользователь'

    def files_count(self, obj):
        return obj.files.count()
    files_count.short_description = 'Файлы'

    def messages_count(self, obj):
        return obj.messages.count()
    messages_count.short_description = 'Сообщения'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user').prefetch_related('files', 'messages')

@admin.register(RequestFile)
class RequestFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'request_link', 'file_size', 'file_type', 'created_at')
    list_filter = ('file_type', 'created_at')
    search_fields = ('file_name', 'request__query')
    readonly_fields = ('file_size', 'file_type', 'created_at')
    ordering = ('-created_at',)

    def request_link(self, obj):
        url = reverse('admin:admin_panel_request_change', args=[obj.request.id])
        return format_html('<a href="{}">{}</a>', url, obj.request)
    request_link.short_description = 'Запрос'

@admin.register(RequestMessage)
class RequestMessageAdmin(admin.ModelAdmin):
    list_display = ('truncated_text', 'request_link', 'is_from_user', 'created_at')
    list_filter = ('is_from_user', 'created_at')
    search_fields = ('text', 'request__query')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    def truncated_text(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    truncated_text.short_description = 'Текст'

    def request_link(self, obj):
        url = reverse('admin:admin_panel_request_change', args=[obj.request.id])
        return format_html('<a href="{}">{}</a>', url, obj.request)
    request_link.short_description = 'Запрос'

@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    list_display = ('ai_assistant_enabled', 'updated_at')
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        # Prevent creating multiple instances
        return not BotSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting the only instance
        return False 
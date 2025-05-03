from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import TelegramUser, Request, RequestFile, RequestMessage

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'first_name', 'last_name', 'created_at')
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

class RequestFileInline(admin.TabularInline):
    model = RequestFile
    extra = 0
    readonly_fields = ('file_preview', 'file_size_display', 'uploaded_at')
    fields = ('file_name', 'file_type', 'file_size_display', 'file_preview', 'uploaded_at')
    
    def file_size_display(self, obj):
        """Отображение размера файла в человекочитаемом формате"""
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        else:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"
    file_size_display.short_description = 'Размер'
    
    def file_preview(self, obj):
        """Отображение превью файла или ссылки на скачивание"""
        if obj.preview_key:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                reverse('request-file-preview', args=[obj.id])
            )
        return format_html(
            '<a href="{}">Скачать файл</a>',
            reverse('request-file-download', args=[obj.id])
        )
    file_preview.short_description = 'Превью'

class RequestMessageInline(admin.TabularInline):
    model = RequestMessage
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('sender_type', 'sender', 'telegram_user', 'message', 'created_at')

@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_user', 'category', 'subject', 'status', 'created_at', 'assigned_to')
    list_filter = ('status', 'category', 'created_at', 'assigned_to')
    search_fields = ('subject', 'message', 'telegram_user__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    inlines = [RequestFileInline, RequestMessageInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('telegram_user', 'category', 'subject', 'message')
        }),
        ('Статус', {
            'fields': ('status', 'assigned_to')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        """Добавляем системное сообщение при изменении статуса"""
        if change and 'status' in form.changed_data:
            RequestMessage.objects.create(
                request=obj,
                sender_type='system',
                message=f'Статус изменен на "{obj.get_status_display()}"'
            )
        super().save_model(request, obj, form, change)

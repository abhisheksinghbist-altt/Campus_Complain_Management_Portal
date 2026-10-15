from django.contrib import admin
from .models import ComplaintAttachment, SystemLog

@admin.register(ComplaintAttachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'complaint', 'uploaded_by', 'file_size', 'mime_type', 'uploaded_at')

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display  = ('action', 'complaint', 'actor', 'description', 'timestamp')
    list_filter   = ('action',)
    readonly_fields = ('timestamp',)

from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import ComplaintAttachment, SystemLog


class AttachmentResource(resources.ModelResource):
    class Meta:
        model  = ComplaintAttachment
        fields = (
            'id', 'complaint__id', 'uploaded_by__username',
            'original_filename', 'file_size', 'mime_type', 'uploaded_at',
        )
        export_order     = fields
        import_id_fields = ('id',)
        skip_unchanged   = True


class SystemLogResource(resources.ModelResource):
    class Meta:
        model  = SystemLog
        fields = ('id', 'action', 'complaint__id', 'actor__username', 'description', 'timestamp')
        export_order     = fields
        import_id_fields = ('id',)
        skip_unchanged   = True


@admin.register(ComplaintAttachment)
class AttachmentAdmin(ImportExportModelAdmin):
    resource_classes = [AttachmentResource]
    list_display = ('original_filename', 'complaint', 'uploaded_by', 'file_size', 'mime_type', 'uploaded_at')


@admin.register(SystemLog)
class SystemLogAdmin(ImportExportModelAdmin):
    resource_classes = [SystemLogResource]
    list_display    = ('action', 'complaint', 'actor', 'description', 'timestamp')
    list_filter     = ('action',)
    readonly_fields = ('timestamp',)

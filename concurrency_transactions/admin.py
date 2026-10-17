from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import StaffWorkload, AssignmentLog


class StaffWorkloadResource(resources.ModelResource):
    class Meta:
        model  = StaffWorkload
        fields = ('id', 'staff__username', 'active_count', 'max_capacity', 'updated_at')
        export_order     = fields
        import_id_fields = ('id',)
        skip_unchanged   = True


class AssignmentLogResource(resources.ModelResource):
    class Meta:
        model  = AssignmentLog
        fields = ('id', 'complaint__id', 'assigned_by__username', 'assigned_to__username',
                  'previous_status', 'new_status', 'timestamp')
        export_order     = fields
        import_id_fields = ('id',)
        skip_unchanged   = True


@admin.register(StaffWorkload)
class StaffWorkloadAdmin(ImportExportModelAdmin):
    resource_classes = [StaffWorkloadResource]
    list_display = ('staff', 'active_count', 'max_capacity', 'updated_at')


@admin.register(AssignmentLog)
class AssignmentLogAdmin(ImportExportModelAdmin):
    resource_classes = [AssignmentLogResource]
    list_display    = ('complaint', 'assigned_by', 'assigned_to', 'previous_status', 'new_status', 'timestamp')
    list_filter     = ('new_status',)
    readonly_fields = ('timestamp',)

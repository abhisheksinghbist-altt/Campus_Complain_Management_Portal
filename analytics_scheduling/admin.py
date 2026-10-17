from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import SchedulingConfig, DashboardSnapshot


class SchedulingConfigResource(resources.ModelResource):
    class Meta:
        model  = SchedulingConfig
        fields = ('id', 'category__name', 'algorithm', 'is_active', 'updated_at')
        export_order     = fields
        import_id_fields = ('id',)
        skip_unchanged   = True


class DashboardSnapshotResource(resources.ModelResource):
    class Meta:
        model  = DashboardSnapshot
        fields = (
            'id', 'snapshot_at', 'total_complaints', 'pending_count',
            'assigned_count', 'in_progress_count', 'resolved_count',
            'closed_count', 'avg_resolution_hrs',
        )
        export_order     = fields
        import_id_fields = ('id',)
        skip_unchanged   = True


@admin.register(SchedulingConfig)
class SchedulingConfigAdmin(ImportExportModelAdmin):
    resource_classes = [SchedulingConfigResource]
    list_display = ('category', 'algorithm', 'is_active', 'updated_at')


@admin.register(DashboardSnapshot)
class DashboardSnapshotAdmin(ImportExportModelAdmin):
    resource_classes = [DashboardSnapshotResource]
    list_display    = ('snapshot_at', 'total_complaints', 'pending_count', 'resolved_count', 'avg_resolution_hrs')
    readonly_fields = ('snapshot_at',)

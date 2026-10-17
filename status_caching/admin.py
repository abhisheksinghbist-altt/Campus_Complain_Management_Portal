from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import StatusUpdate, CacheMetric


class StatusUpdateResource(resources.ModelResource):
    class Meta:
        model  = StatusUpdate
        fields = ('id', 'complaint__id', 'updated_by__username', 'old_status', 'new_status', 'note', 'timestamp')
        export_order     = fields
        import_id_fields = ('id',)
        skip_unchanged   = True


class CacheMetricResource(resources.ModelResource):
    class Meta:
        model  = CacheMetric
        fields = ('id', 'key', 'hit', 'latency_ms', 'timestamp')
        export_order     = fields
        import_id_fields = ('id',)
        skip_unchanged   = True


@admin.register(StatusUpdate)
class StatusUpdateAdmin(ImportExportModelAdmin):
    resource_classes = [StatusUpdateResource]
    list_display = ('complaint', 'updated_by', 'old_status', 'new_status', 'timestamp')
    list_filter  = ('new_status',)


@admin.register(CacheMetric)
class CacheMetricAdmin(ImportExportModelAdmin):
    resource_classes = [CacheMetricResource]
    list_display = ('key', 'hit', 'latency_ms', 'timestamp')
    list_filter  = ('hit',)

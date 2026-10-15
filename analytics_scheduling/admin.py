from django.contrib import admin
from .models import SchedulingConfig, DashboardSnapshot

@admin.register(SchedulingConfig)
class SchedulingConfigAdmin(admin.ModelAdmin):
    list_display = ('category', 'algorithm', 'is_active', 'updated_at')

@admin.register(DashboardSnapshot)
class DashboardSnapshotAdmin(admin.ModelAdmin):
    list_display = ('snapshot_at', 'total_complaints', 'pending_count', 'resolved_count', 'avg_resolution_hrs')
    readonly_fields = ('snapshot_at',)

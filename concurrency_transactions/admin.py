from django.contrib import admin
from .models import StaffWorkload, AssignmentLog

@admin.register(StaffWorkload)
class StaffWorkloadAdmin(admin.ModelAdmin):
    list_display = ('staff', 'active_count', 'max_capacity', 'updated_at')

@admin.register(AssignmentLog)
class AssignmentLogAdmin(admin.ModelAdmin):
    list_display  = ('complaint', 'assigned_by', 'assigned_to', 'previous_status', 'new_status', 'timestamp')
    list_filter   = ('new_status',)
    readonly_fields = ('timestamp',)

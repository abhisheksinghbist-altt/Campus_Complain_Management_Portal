from django.contrib import admin
from .models import StatusUpdate, CacheMetric

@admin.register(StatusUpdate)
class StatusUpdateAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'updated_by', 'old_status', 'new_status', 'timestamp')
    list_filter  = ('new_status',)

@admin.register(CacheMetric)
class CacheMetricAdmin(admin.ModelAdmin):
    list_display = ('key', 'hit', 'latency_ms', 'timestamp')
    list_filter  = ('hit',)

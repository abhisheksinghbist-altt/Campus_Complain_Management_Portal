"""
Module 6: Status Tracking & Memory Caching
DBMS Focus: SELECT/WHERE queries for per-student history.
OS Focus: File-based caching to reduce DB load.
"""
from django.db import models
from django.conf import settings


class StatusUpdate(models.Model):
    """
    Every status change on a complaint is recorded here.
    Students use this to track progress of their active tickets.
    """
    complaint  = models.ForeignKey(
        'submission_monitoring.Complaint',
        on_delete=models.CASCADE,
        related_name='status_updates'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    note       = models.TextField(blank=True,
                                  help_text='Optional staff remark on this update')
    timestamp  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'status_updates'
        ordering = ['-timestamp']
        indexes  = [models.Index(fields=['complaint', 'timestamp'])]

    def __str__(self):
        return (f"Complaint #{self.complaint_id}: "
                f"{self.old_status} → {self.new_status}")


class CacheMetric(models.Model):
    """
    Records cache hit/miss events to demonstrate memory vs disk performance.
    Used in the dashboard to show caching effectiveness (OS concept).
    """
    key       = models.CharField(max_length=200)
    hit       = models.BooleanField(help_text='True = cache hit, False = DB query')
    latency_ms = models.FloatField(help_text='Time taken in milliseconds')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cache_metrics'
        ordering = ['-timestamp']

    def __str__(self):
        result = 'HIT' if self.hit else 'MISS'
        return f"[{result}] {self.key} ({self.latency_ms}ms)"

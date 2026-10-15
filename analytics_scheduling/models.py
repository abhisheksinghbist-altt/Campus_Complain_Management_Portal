"""
Module 3: Analytics & Task Scheduling Algorithms
DBMS Focus: Complex JOINs, aggregate functions, DB Views.
OS Focus: CPU scheduling algorithms (Priority / SJF) for auto-assignment.
"""
from django.db import models
from django.conf import settings


class SchedulingConfig(models.Model):
    """
    Admin-configurable scheduling algorithm per category.
    Allows switching between Priority Scheduling and SJF at runtime.
    """
    ALGORITHM_CHOICES = [
        ('priority', 'Priority Scheduling'),
        ('sjf',      'Shortest Job First'),
        ('fcfs',     'First Come First Served'),
    ]

    category  = models.OneToOneField(
        'submission_monitoring.Category',
        on_delete=models.CASCADE,
        related_name='scheduling_config'
    )
    algorithm = models.CharField(max_length=20, choices=ALGORITHM_CHOICES,
                                 default='priority')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'scheduling_configs'

    def __str__(self):
        return f"{self.category.name} → {self.algorithm}"


class DashboardSnapshot(models.Model):
    """
    Periodic snapshot of dashboard stats — avoids expensive re-computation.
    Populated by the scheduled analytics task (can also be cron-driven).
    """
    snapshot_at        = models.DateTimeField(auto_now_add=True)
    total_complaints   = models.PositiveIntegerField(default=0)
    pending_count      = models.PositiveIntegerField(default=0)
    in_progress_count  = models.PositiveIntegerField(default=0)
    resolved_count     = models.PositiveIntegerField(default=0)
    avg_resolution_hrs = models.FloatField(default=0.0)
    # JSON field for department-wise breakdown
    dept_stats         = models.JSONField(default=dict)

    class Meta:
        db_table = 'dashboard_snapshots'
        ordering = ['-snapshot_at']
        get_latest_by = 'snapshot_at'

    def __str__(self):
        return f"Snapshot @ {self.snapshot_at} — {self.total_complaints} total"

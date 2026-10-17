"""
Module 1: Concurrency & Transaction Management
DBMS Focus: ACID transactions — assigning a ticket atomically.
OS Focus: Mutex/semaphore patterns to prevent race conditions.
"""
from django.db import models
from django.conf import settings


class StaffWorkload(models.Model):
    """
    Tracks active task count per staff member.
    Updated atomically inside a DB transaction (Module 1 logic).
    Used to prevent assigning too many tasks to one staff member.
    """
    staff        = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workload'
    )
    active_count = models.PositiveIntegerField(default=0)
    max_capacity = models.PositiveIntegerField(default=5)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff_workload'

    def is_available(self):
        return self.active_count < self.max_capacity

    def __str__(self):
        return f"{self.staff} — {self.active_count}/{self.max_capacity} tasks"


class AssignmentLog(models.Model):
    """
    Audit trail for every ticket assignment.
    Written inside the atomic transaction so any rollback removes this too.
    """
    complaint    = models.ForeignKey(
        'submission_monitoring.Complaint',
        on_delete=models.CASCADE,
        related_name='assignment_logs'
    )
    assigned_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='assignments_made'
    )
    assigned_to  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='assignments_received'
    )
    previous_status = models.CharField(max_length=20)
    new_status      = models.CharField(max_length=20)
    timestamp       = models.DateTimeField(auto_now_add=True)
    notes           = models.TextField(blank=True)

    class Meta:
        db_table = 'assignment_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"Complaint #{self.complaint_id} → {self.assigned_to} at {self.timestamp}"

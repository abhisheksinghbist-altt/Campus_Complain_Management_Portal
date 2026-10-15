"""
Module 2: Engine & File System Architecture
DBMS Focus: Schema design + Triggers (auto-log status changes).
OS Focus: Secure file handling, directory permissions, inode concepts.
"""
from django.db import models
from django.conf import settings
import os


def complaint_attachment_path(instance, filename):
    """
    Isolates each complaint's files under its own directory.
    Concept: inode-per-complaint directory — prevents path traversal.
    e.g.  media/complaints/<complaint_id>/<filename>
    """
    return os.path.join('complaints', str(instance.complaint_id), filename)


class ComplaintAttachment(models.Model):
    """
    Stores metadata for uploaded files linked to a complaint.
    Actual files live on disk under MEDIA_ROOT with restricted permissions.
    """
    complaint   = models.ForeignKey(
        'submission_monitoring.Complaint',
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True
    )
    file        = models.FileField(upload_to=complaint_attachment_path)
    original_filename = models.CharField(max_length=255)
    file_size   = models.PositiveIntegerField(help_text='Size in bytes')
    mime_type   = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'complaint_attachments'

    def __str__(self):
        return f"{self.original_filename} for Complaint #{self.complaint_id}"


class SystemLog(models.Model):
    """
    Automated system-level logs — mirrors what a DB Trigger would write.
    In production this table is also populated by PostgreSQL triggers
    (see file_engine/sql/triggers.sql).
    """
    ACTION_CHOICES = [
        ('status_change', 'Status Change'),
        ('assignment',    'Assignment'),
        ('file_upload',   'File Upload'),
        ('login',         'Login'),
        ('logout',        'Logout'),
        ('db_backup',     'DB Backup'),
    ]

    action      = models.CharField(max_length=30, choices=ACTION_CHOICES)
    complaint   = models.ForeignKey(
        'submission_monitoring.Complaint',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='system_logs'
    )
    actor       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True
    )
    description = models.TextField()
    old_value   = models.CharField(max_length=100, blank=True)
    new_value   = models.CharField(max_length=100, blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_logs'
        indexes  = [models.Index(fields=['action', 'timestamp'])]
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.action}] {self.description[:60]}"

"""
Module 5: Submission Engine & Process Monitoring
DBMS Focus: INSERT queries for complaint submission.
OS Focus: Process health-check script.
"""
from django.db import models
from django.conf import settings


class Category(models.Model):
    """Complaint categories — normalized to avoid repeating strings."""
    name       = models.CharField(max_length=50, unique=True)
    priority   = models.PositiveSmallIntegerField(
        default=3,
        help_text='1=Critical, 2=High, 3=Medium, 4=Low — used by Module 3 scheduler'
    )
    avg_resolution_hours = models.FloatField(
        default=24.0,
        help_text='Historical average — used for SJF scheduling in Module 3'
    )

    class Meta:
        db_table     = 'complaint_categories'
        ordering     = ['priority']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Complaint(models.Model):
    """
    Core complaint table — the central entity of the portal.
    Normalized to 3NF: category, submitter, and assigned_to are FKs.
    """
    STATUS_CHOICES = [
        ('pending',     'Pending'),
        ('assigned',    'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved',    'Resolved'),
        ('closed',      'Closed'),
    ]

    LOCATION_CHOICES = [
        ('classroom', 'Classroom'),
        ('hostel',    'Hostel'),
        ('lab',       'Lab'),
        ('office',    'Office'),
        ('canteen',   'Canteen'),
        ('library',   'Library'),
        ('other',     'Other'),
    ]

    title        = models.CharField(max_length=200)
    description  = models.TextField()
    category     = models.ForeignKey(Category, on_delete=models.PROTECT,
                                     related_name='complaints')
    location     = models.CharField(max_length=50, choices=LOCATION_CHOICES)
    location_detail = models.CharField(max_length=100, blank=True,
                                       help_text='e.g. Room 204, Block C')
    submitter    = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.CASCADE,
                                     related_name='submitted_complaints')
    assigned_to  = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     related_name='assigned_complaints')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                    default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    resolved_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'complaints'
        indexes  = [
            models.Index(fields=['status']),
            models.Index(fields=['submitter']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['category']),
            models.Index(fields=['submitted_at']),
        ]
        ordering = ['-submitted_at']

    rating = models.PositiveSmallIntegerField(null=True, blank=True, help_text='1-5 star rating by submitter after resolution')

    def resolution_hours(self):
        """Returns hours taken to resolve, or None if not resolved."""
        if self.resolved_at and self.submitted_at:
            delta = self.resolved_at - self.submitted_at
            return round(delta.total_seconds() / 3600, 2)
        return None

    def __str__(self):
        return f"[{self.status.upper()}] {self.title} by {self.submitter}"

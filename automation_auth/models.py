"""
Module 4: Automation & Authentication
DBMS Focus: Role-based access control, CRUD for users.
OS Focus: Shell scripting + cron for DB backups.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class CampusUser(AbstractUser):
    """
    Extended user model with campus-specific roles.
    Normalized to 3NF — role is a FK to avoid repeating role strings.
    """
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('staff',   'Staff'),
        ('admin',   'Admin'),
    ]

    role         = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    department   = models.CharField(max_length=100, blank=True)
    phone        = models.CharField(max_length=15, blank=True)
    hostel_block = models.CharField(max_length=10, blank=True,
                                    help_text='Relevant for hostel complaints')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'campus_users'
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['department']),
        ]

    def is_admin(self):
        return self.role == 'admin'

    def is_staff_member(self):
        return self.role == 'staff'

    def is_student_or_faculty(self):
        return self.role in ('student', 'faculty')

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

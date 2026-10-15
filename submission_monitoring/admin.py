from django.contrib import admin
from .models import Complaint, Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority', 'avg_resolution_hours')

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display  = ('id', 'title', 'category', 'status', 'submitter', 'assigned_to', 'submitted_at')
    list_filter   = ('status', 'category', 'location')
    search_fields = ('title', 'description')
    date_hierarchy = 'submitted_at'

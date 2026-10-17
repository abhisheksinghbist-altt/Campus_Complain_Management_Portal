from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Complaint, Category


class CategoryResource(resources.ModelResource):
    class Meta:
        model  = Category
        fields = ('id', 'name', 'priority', 'avg_resolution_hours')
        import_id_fields = ('name',)
        skip_unchanged   = True


class ComplaintResource(resources.ModelResource):
    class Meta:
        model  = Complaint
        fields = (
            'id', 'title', 'description', 'category__name',
            'location', 'location_detail',
            'submitter__username', 'assigned_to__username',
            'status', 'submitted_at', 'resolved_at', 'rating',
        )
        export_order     = fields
        import_id_fields = ('id',)
        skip_unchanged   = True


@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin):
    resource_classes = [CategoryResource]
    list_display = ('name', 'priority', 'avg_resolution_hours')


@admin.register(Complaint)
class ComplaintAdmin(ImportExportModelAdmin):
    resource_classes = [ComplaintResource]
    list_display   = ('id', 'title', 'category', 'status', 'submitter', 'assigned_to', 'submitted_at')
    list_filter    = ('status', 'category', 'location')
    search_fields  = ('title', 'description')
    date_hierarchy = 'submitted_at'

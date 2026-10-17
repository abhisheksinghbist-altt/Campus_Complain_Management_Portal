from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import CampusUser


class CampusUserResource(resources.ModelResource):
    class Meta:
        model  = CampusUser
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email',
            'role', 'department', 'phone', 'hostel_block',
            'is_active', 'date_joined',
        )
        export_order     = fields
        import_id_fields = ('username',)
        skip_unchanged   = True

    def before_import_row(self, row, row_number=None, **kwargs):
        """Set a default password for new imports if none supplied."""
        if not row.get('password'):
            row['password'] = 'Campus@2025'

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        """Hash plain-text passwords on import."""
        raw_pw = getattr(instance, '_import_raw_password', None)
        if new and not instance.password.startswith('pbkdf2_'):
            instance.set_password(instance.password)


@admin.register(CampusUser)
class CampusUserAdmin(ImportExportModelAdmin, UserAdmin):
    resource_classes = [CampusUserResource]
    list_display   = ('username', 'get_full_name', 'role', 'department', 'email', 'is_active')
    list_filter    = ('role', 'department', 'is_active')
    search_fields  = ('username', 'first_name', 'last_name', 'email')
    fieldsets = UserAdmin.fieldsets + (
        ('Campus Info', {'fields': ('role', 'department', 'phone', 'hostel_block')}),
    )

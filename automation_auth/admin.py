from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CampusUser

@admin.register(CampusUser)
class CampusUserAdmin(UserAdmin):
    list_display  = ('username', 'get_full_name', 'role', 'department', 'email')
    list_filter   = ('role', 'department')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    fieldsets = UserAdmin.fieldsets + (
        ('Campus Info', {'fields': ('role', 'department', 'phone', 'hostel_block')}),
    )

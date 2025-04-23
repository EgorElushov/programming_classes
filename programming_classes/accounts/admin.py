from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Account, Role


class RoleInline(admin.StackedInline):
    model = Role
    can_delete = False
    verbose_name_plural = 'Role Information'


class AccountAdmin(BaseUserAdmin):
    inlines = (RoleInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff')
    list_filter = ('role__role_type', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    def get_role(self, obj):
        return obj.role.get_role_type_display()

    get_role.short_description = 'Role'


admin.site.register(Account, AccountAdmin)
admin.site.register(Role)

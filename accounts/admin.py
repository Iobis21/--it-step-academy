from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'personal_id', 'phone', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'personal_id', 'phone']
    fieldsets = UserAdmin.fieldsets + (('დამატებითი', {'fields': ('personal_id', 'phone')}),)

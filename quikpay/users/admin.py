from django.contrib import admin
from .models import User

# Register your models here.

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    exclude = ('password',)
    list_display = ('email', 'phone_number', 'first_name', 'last_name', 'id_number', 'status')
    search_fields = ('email', 'phone_number', 'first_name', 'last_name', 'id_number')
    list_filter = ('status',)

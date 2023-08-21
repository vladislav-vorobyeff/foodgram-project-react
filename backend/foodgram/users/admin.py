from django.contrib import admin
from users.models import CustomUser, Subscriptions


class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff'
    )
    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff'
    )


class SubscriptionsAdmin(admin.ModelAdmin):
    list_display = ('author', 'user', 'add_date')
    search_fields = ('author', 'user', 'add_date')


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Subscriptions, SubscriptionsAdmin)

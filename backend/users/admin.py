from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import Subscriptions

User = get_user_model()


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
    )
    search_fields = ('email', 'username')
    list_filter = ('email', 'first_name')
    fields = (
        ("username",),
        ("email",),
        ("first_name",),
        ("last_name",),
        ("password",),
    )


@admin.register(Subscriptions)
class SubscriptionSAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'following'
    )

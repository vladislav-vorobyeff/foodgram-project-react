from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from .validators import validate_username_me


class CustomUser(AbstractUser):
    username = models.CharField(
        'username',
        max_length=200,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[\w.@+-]+$",
                message="Некорректный username",
            ),
            validate_username_me,
        ],
    )
    first_name = models.CharField(
        'Имя',
        max_length=200
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=200
    )
    email = models.EmailField(
        'Email',
        max_length=200,
        unique=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'password', 'first_name', 'last_name')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-id']


class Subscriptions(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='subscriber',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='author',
        verbose_name='Автор'
    )
    add_date = models.DateTimeField(
        'Дата подписки',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ['-add_date']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_subscribe'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='user is not author',
                violation_error_message={'check': 'Пользователь - не автор'}
            )
        ]

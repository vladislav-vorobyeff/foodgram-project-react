from django.db import models

from colorfield.fields import ColorField

class Tag(models.Model):
    name = models.CharField(
        unique=True,
        max_length=200,
        verbose_name='Тег'
    )
    color = ColorField(
        'Цвет',
        max_length=7,
        format='hex',
        unique=True
    )
    slug = models.SlugField(
        unique=True,
        max_length=200,
        verbose_name='slug'
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name

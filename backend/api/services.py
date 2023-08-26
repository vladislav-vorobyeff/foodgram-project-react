from base64 import b64decode

from django.core.files.base import ContentFile
from recipes.models import Ingredient
from rest_framework.serializers import ImageField


class Base64ImageField(ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


def generate_shopping_cart_text(ingredients_to_buy):
    shopping_cart_text = 'Список покупок:\n'
    for item in ingredients_to_buy:
        ingredient = Ingredient.objects.get(pk=item['ingredient'])
        amount = item['amount']
        shopping_cart_text += (
            f'{ingredient.name}'
            f'({ingredient.measurement_unit}) - {amount}\n'
        )
    return shopping_cart_text

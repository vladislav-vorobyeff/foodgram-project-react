from django_filters.rest_framework import DjangoFilterBackend
from ingredients.models import Ingredient
from rest_framework.viewsets import ReadOnlyModelViewSet

from ..filters import IngredientFilter
from .serializers import IngredientSerializer


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter

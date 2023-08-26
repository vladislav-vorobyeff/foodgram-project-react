from api.filters import RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from favorites.models import Favorite
from recipes.models import IngredientRecipe, Recipe
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from shoppingcarts.models import ShoppingCart

from ..services import generate_shopping_cart_text
from ..users.serializers import RecipeShortSerializer
from .serializers import (RecipeCreateSerializer, RecipeSerializer,
                          ShoppingCartSerializer)


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return RecipeCreateSerializer
        return RecipeSerializer

    @action(
        detail=True,
        methods=['POST'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user
        if user.is_authenticated:
            if not Favorite.objects.filter(
                user=user,
                recipe=recipe
            ).exists():
                Favorite.objects.create(
                    user=user,
                    recipe=recipe
                )
                serializer = RecipeShortSerializer(
                    recipe,
                    context={'request': request}
                )
                return Response(serializer.data)
            return Response(
                'Рецепт уже в избранном',
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            'Требуется авторизация',
            status=status.HTTP_401_UNAUTHORIZED
        )

    @favorite.mapping.delete
    def remove_favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user
        if user.is_authenticated:
            favorite = Favorite.objects.filter(
                user=user, recipe=recipe)
            if favorite.exists():
                favorite.delete()
                return Response('Удален из избранного')
            return Response(
                'Рецепта нет в избранном',
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            'Необходма авторизация',
            status=status.HTTP_401_UNAUTHORIZED
        )

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=[IsAuthenticatedOrReadOnly]
    )
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        if request.method == 'POST':
            recipe, created = ShoppingCart.objects.get_or_create(
                user=user, recipe=recipe
            )
            if created is True:
                serializer = ShoppingCartSerializer()
                return Response(
                    serializer.to_representation(instance=recipe),
                    status=status.HTTP_201_CREATED
                )
            return Response(
                {'errors': 'Рецепт уже в корзине покупок'},
                status=status.HTTP_201_CREATED
            )
        if request.method == 'DELETE':
            ShoppingCart.objects.filter(
                user=user, recipe=recipe
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        shopping_cart = ShoppingCart.objects.filter(user=self.request.user)
        recipes_in_shopping_cart = [item.recipe.id for item in shopping_cart]
        ingredients_to_buy = IngredientRecipe.objects.filter(
            recipe__in=recipes_in_shopping_cart).values('ingredient').annotate(
                amount=Sum('amount'))

        shopping_cart_text = generate_shopping_cart_text(ingredients_to_buy)

        return FileResponse(
            shopping_cart_text,
            content_type="text/plain",
            filename='shopping_cart.txt'
        )

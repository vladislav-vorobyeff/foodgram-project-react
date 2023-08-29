from django.http import HttpResponse
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from favorites.models import Favorite
from shoppingcarts.models import ShoppingCart
from recipes.models import IngredientRecipe, Recipe
from api.filters import RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from ..users.serializers import RecipeShortSerializer
from .serializers import RecipeCreateSerializer, RecipeSerializer


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
        methods=['POST'],
        permission_classes=[IsAuthenticatedOrReadOnly]
    )
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        if ShoppingCart.objects.filter(user=request.user,
                                       recipe=recipe).exists():
            return Response(
                {'errors': 'УЖе находится в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST
            )
        ShoppingCart.objects.create(user=request.user, recipe=recipe)
        serializer = RecipeShortSerializer(recipe, many=False)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def remove_from_shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        get_object_or_404(ShoppingCart, user=request.user,
                          recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DownloadShoppingCartViewSet(APIView):
    def get(self, request):
        ingredients = IngredientRecipe.objects.filter(
            recipe__shopping_cart__user=request.user).values(
                'ingredient__name', 'ingredient__measurement_unit').annotate(
                    amount=Sum('amount')
        )
        shop_string = (
            'Ингредиенты к покупке:\n\n')
        shop_string += '\n'.join([
            f'- {ingredient["ingredient__name"]}, '
            f'{ingredient["ingredient__measurement_unit"]}: '
            f'{ingredient["amount"]}'
            for ingredient in ingredients
        ])
        response = HttpResponse(
            shop_string,
            content_type='text/plain, charset=utf8'
        )
        response['Content-Disposition'] = 'attachment; '
        'filename="shopping_list.txt"'
        return response

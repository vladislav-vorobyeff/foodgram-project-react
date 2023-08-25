from api.filters import IngredientFilter, RecipesFilter
from api.pagination import CustomPagination
from api.serializers import (IngredientSerializer, RecipeGetSerializer,
                             RecipeSerializer, ShortRecipeSerializer,
                             SubscriptionsSerializer, TagSerializer,
                             UserSerializer)
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from users.models import CustomUser, Subscriptions


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = [IngredientFilter]
    search_fields = ('^name',)


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipesFilter

    def get_serializer_class(self):
        if self.action in ['create', 'partial_update']:
            return RecipeSerializer
        return RecipeGetSerializer

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(author=user)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, recipe_id):
        recipe = get_object_or_404(Recipe, id=recipe_id)
        if Favorite.objects.filter(user=request.user,
                                   recipe=recipe).exists():
            return Response(
                {'errors': 'Уже добавлен в избранное'},
                status=status.HTTP_400_BAD_REQUEST
            )
        Favorite.objects.create(user=request.user, recipe=recipe)
        serializer = ShortRecipeSerializer(recipe, many=False)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def del_favorite(self, request, recipe_id):
        recipe = get_object_or_404(Recipe, id=recipe_id)
        if not Favorite.objects.filter(user=request.user,
                                       recipe=recipe).exists():
            return Response(
                {'errors': 'Этого репета нет в избранном'},
                status=status.HTTP_400_BAD_REQUEST
            )
        get_object_or_404(Favorite, user=request.user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['POST'],
        permission_classes=(IsAuthenticated,),
    )
    def shopping_cart(self, request, recipe_id):
        recipe = get_object_or_404(Recipe, id=recipe_id)
        if ShoppingCart.objects.filter(user=request.user,
                                       recipe=recipe).exists():
            return Response(
                {'errors': 'УЖе находится в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST
            )
        ShoppingCart.objects.create(user=request.user, recipe=recipe)
        serializer = ShortRecipeSerializer(recipe, many=False)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, recipe_id):
        recipe = get_object_or_404(Recipe, id=recipe_id)
        if not ShoppingCart.objects.filter(user=request.user,
                                           recipe=recipe).exists():
            return Response(
                {'errors': 'Нет в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST
            )
        get_object_or_404(ShoppingCart, user=request.user,
                          recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DownloadShoppingCartViewSet(APIView):
    def get(self, request):
        ingredient_list = 'Cписок покупок:'
        ingredients = IngredientRecipe.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(amount_sum=Sum('amount'))
        for num, i in enumerate(ingredients):
            ingredient_list += (
                f"\n{i['ingredient__name']} - "
                f"{i['amount_sum']} {i['ingredient__measurement_unit']}"
            )
            if num < ingredients.count() - 1:
                ingredient_list += ', '
        response = HttpResponse(
            ingredient_list, content_type='text/plain, charset=utf8'
        )
        response['Content-Disposition'] = 'attachment; '
        'filename="shopping_list.txt"'
        return response


class UserViewSet(UserViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == "subscriptions":
            return SubscriptionsSerializer
        return UserSerializer

    @action(
        detail=False,
        methods=['GET'],
        serializer_class=SubscriptionsSerializer,
        permission_classes=(IsAuthenticated, )
    )
    def subscriptions(self, request):
        queryset = CustomUser.objects.filter(user_follower__user=request.user)
        paginated_queryset = self.paginate_queryset(queryset)
        serializer = self.get_serializer(paginated_queryset, many=True)

        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['POST'],
        serializer_class=SubscriptionsSerializer
    )
    def subscribe(self, request, author_id):
        author = get_object_or_404(CustomUser, id=author_id)
        if Subscriptions.objects.filter(user=request.user,
                                        author=author).exists():
            return Response(
                {'errors': 'Вы уже подписаны на этого автора'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if request.user == author:
            return Response(
                {'errors': 'Нельзя подписаться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST
            )
        Subscriptions.objects.create(user=request.user, author=author)
        serializer = SubscriptionsSerializer(
            get_object_or_404(Subscriptions, user=request.user,
                              author=author),
            many=False
        )
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, author_id):
        author = get_object_or_404(CustomUser, id=author_id)
        get_object_or_404(Subscriptions, user=request.user,
                          author=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

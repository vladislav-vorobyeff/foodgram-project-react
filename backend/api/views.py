from api.filters import IngredientFilter, RecipesFilter
from api.pagination import CustomPagination
from api.serializers import (IngredientSerializer, RecipeGetSerializer,
                             RecipeSerializer, ShortRecipeSerializer,
                             SubscriptionsSerializer, TagSerializer,
                             UserSerializer)
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
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
    permission_classes = [AllowAny]


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipesFilter

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return RecipeSerializer
        return RecipeGetSerializer

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(author=user)

    @action(
        detail=True,
        methods=("post", "delete",),
        permission_classes=(IsAuthenticated,),
        url_path=r"favorite"
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == "POST":
            if Favorite.objects.filter(user=request.user,
                                       recipe=recipe).exists():
                return Response(
                    {'errors': 'Уже добавлен в избранное'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(user=request.user, recipe=recipe)
            serializer = ShortRecipeSerializer(recipe, many=False)
            return Response(data=serializer.data,
                            status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            if not Favorite.objects.filter(user=request.user,
                                           recipe=recipe).exists():
                return Response(
                    {'errors': 'Этого репета нет в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            get_object_or_404(Favorite,
                              user=request.user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=("post", "delete",),
        permission_classes=(IsAuthenticated,),
        url_path=r"shopping_cart"
    )
    def shopping_cart(self, request, recipe_id):
        recipe = get_object_or_404(Recipe, id=recipe_id)

        if request.method == "POST":
            if ShoppingCart.objects.filter(user=request.user,
                                           recipe=recipe).exists():
                return Response(
                    {'errors': 'УЖе находится в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            serializer = ShortRecipeSerializer(recipe, many=False)
            return Response(data=serializer.data,
                            status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
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
        user = request.user
        recipes_list = ShoppingCart.objects.filter(user=user).values('recipe')
        recipes = Recipe.objects.filter(pk__in=recipes_list)
        shopping_list_dict = {}
        recipe_count = 0
        for recipe in recipes:
            recipe_count = recipe_count + 1
            ing_amounts_list = IngredientRecipe.objects.filter(recipe=recipe)
            for ing in ing_amounts_list:
                if ing.ingredient.name in shopping_list_dict:
                    shopping_list_dict[ing.ingredient.name][0] += ing.amount
                else:
                    shopping_list_dict[ing.ingredient.name] = [
                        ing.amount, ing.ingredient.measurement_unit
                    ]

    def download_cart(self, recipe_count, shopping_list_dict):
        shop_string = (
            f'Количество рецептов: {recipe_count}\n\n'
            f'Ингредиенты к покупке:\n\n')
        for key, value in shopping_list_dict.items():
            shop_string += f'{key} ({value[1]}) - {str(value[0])}\n'
        response = HttpResponse(
            shop_string,
            content_type='text/plain, charset=utf8'
        )
        response['Content-Disposition'] = 'attachment; '
        'filename="shopping_list.txt"'
        return response


class UserViewSet(UserViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    pagination_class = CustomPagination

    @action(
        detail=True,
        methods=("post", "delete",),
        permission_classes=(IsAuthenticated,),
        url_path=r"subscribe"
    )
    def subscribe(self, request, id=None):
        current_user = request.user
        following_user = get_object_or_404(CustomUser, id=id)
        follow = Subscriptions.objects.filter(
            subscriber=current_user,
            author=following_user
        ).exists()

        if request.method == "POST":
            if current_user == following_user:
                return Response(
                    {'message': 'Нельзя подписываться на самого себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if follow:
                return Response(
                    {'message': 'Вы уже подписаны на этого автора'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscriptions.objects.create(
                subscriber=current_user, author=following_user
            )
            serializer = SubscriptionsSerializer(following_user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            if follow:
                follow = Subscriptions.objects.get(
                    subscriber=current_user, author=following_user
                ).delete()
            return Response(
                {'message': 'Вы отписались от этого пользователя'},
                status=status.HTTP_204_NO_CONTENT
            )
        return Response(
            {'message': 'Вы не подписаны на этого пользователя'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
        url_path=r"subscriptions"
    )
    def subscriptions(self, request):
        subscriptions = self.list(request)
        return subscriptions

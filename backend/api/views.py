from api.filters import IngredientFilter, RecipesFilter
from api.pagination import CustomPagination
from api.serializers import (IngredientSerializer, RecipeGetSerializer,
                             RecipeSerializer, SubscriptionsSerializer,
                             TagSerializer, UserSerializer)
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
    filter_backends = (IngredientFilter)
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
        url_path='favorite',
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, pk=None):
        if request.method == 'POST':
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                recipe = Recipe.objects.get(pk=pk)
                if Favorite.objects.filter(recipe=recipe, user=request.user):
                    return Response(
                        {'errors': 'Рецепт уже добавлен в избранное'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                serializer.save(user=self.request.user, recipe=recipe)
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            favorite = Favorite.objects.filter(recipe=pk, user=request.user)
            if favorite:
                favorite.delete()
                return Response(
                    {'message': f'Рецепт {pk} удален из избранного'},
                    status=status.HTTP_204_NO_CONTENT,
                )
            return Response(
                {'errors': 'Рецепт не добавлен в избранное'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(
        detail=True,
        url_path='shopping_cart',
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,),
    )
    def shopping_cart(self, request, pk=None):
        if request.method == 'POST':
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                recipe = Recipe.objects.get(pk=pk)
                if ShoppingCart.objects.filter(recipe=recipe,
                                               user=request.user):
                    return Response(
                        {'errors': 'Рецепт уже добавлен в список покупок'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                serializer.save(user=self.request.user, recipe=recipe)
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            recipe = Recipe.objects.get(pk=pk)
            shopping_cart = ShoppingCart.objects.filter(
                recipe=recipe, user=request.user
            )
            if shopping_cart:
                shopping_cart.delete()
                return Response(
                    {'message': f'Рецепт {pk} удален из списка покупок'},
                    status=status.HTTP_204_NO_CONTENT,
                )
            return Response(
                {'errors': 'Рецепт не добавлен в список покупок'},
                status=status.HTTP_400_BAD_REQUEST,
            )


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

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, **kwargs):
        user = request.user
        author_id = self.kwargs.get('id')
        author = get_object_or_404(CustomUser, id=author_id)

        if request.method == 'POST':
            serializer = SubscriptionsSerializer(author,
                                                 data=request.data,
                                                 context={'request': request})
            serializer.is_valid(raise_exception=True)
            Subscriptions.objects.create(user=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        subscription = get_object_or_404(Subscriptions,
                                         user=user,
                                         author=author)
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        user = request.user
        queryset = CustomUser.objects.filter(author__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscriptionsSerializer(pages,
                                             many=True,
                                             context={'request': request})
        return self.get_paginated_response(serializer.data)

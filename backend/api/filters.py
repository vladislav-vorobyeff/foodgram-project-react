from django_filters.rest_framework import (BooleanFilter, FilterSet,
                                           ModelChoiceFilter,
                                           ModelMultipleChoiceFilter)
from recipes.models import Recipe, Tag
from rest_framework.filters import SearchFilter
from users.models import CustomUser
from ingredients.models import Ingredient


class IngredientFilter(SearchFilter):
    search_param = 'name'

    class Meta:
        model = Ingredient
        fields = ['name']


class RecipeFilter(FilterSet):
    tags = ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug'
    )
    author = ModelChoiceFilter(
        queryset=CustomUser.objects.all(),
    )
    is_in_shopping_cart = BooleanFilter(method='get_is_in_shopping_cart')
    is_favorited = BooleanFilter(method='get_is_favorited')

    class Meta:
        model = Recipe
        fields = ('tags', 'author', 'is_in_shopping_cart', 'is_favorited')

    def get_is_in_shopping_cart(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(shopping_carts__user=self.request.user)
        return queryset

    def get_is_favorited(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(users_favorites__user=self.request.user)
        return queryset

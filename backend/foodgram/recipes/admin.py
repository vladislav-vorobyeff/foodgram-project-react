from django.contrib import admin
from django.contrib.admin import display
from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)


class IngredientRecipeInLine(admin.TabularInline):
    model = IngredientRecipe
    min_num = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = (IngredientRecipeInLine,)
    list_display = (
        'id', 'name', 'author', 'cooking_time', 'how_many_times_favorited')
    readonly_fields = ('how_many_times_favorited',)
    search_fields = ('name', 'author__username', 'author__email',)
    list_filter = ('name', 'author', 'tags',)

    @display(description='Количество в избранных')
    def how_many_times_favorited(self, obj):
        return obj.favorites.count()


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'color', 'slug',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe',)


@admin.register(IngredientRecipe)
class IngredientRecipe(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount',)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe',)

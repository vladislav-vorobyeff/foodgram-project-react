from django.contrib import admin
from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag, TagRecipe)


class TagAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'color',
        'slug'
    )
    search_fields = (
        'name',
    )


class IngedientAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'measurement_unit'
    )
    search_fields = (
        'name',
    )


class IngredientRecipeInLine(admin.TabularInline):
    model = IngredientRecipe
    extra = 2
    min_num = 1


class TagRecipeInLine(admin.TabularInline):
    model = TagRecipe
    extra = 2
    min_num = 1


class RecipeAdmin(admin.ModelAdmin):
    inlines = (IngredientRecipeInLine, TagRecipeInLine,)
    list_display = (
        'id',
        'author',
        'name',
        'image',
        'text',
        'cooking_time',
        'how_many_times_favorited',
    )
    search_fields = (
        'name',
        'author',
        'tags',
    )

    @admin.display(description='кол-во в избранном')
    def how_many_times_favorited(self, obj):
        return obj.users_favorites.count()


class FavoriteAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
        'add_date'
    )
    search_fields = (
        'user',
        'recipe',
        'add_date'
    )


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
        'add_date'
    )
    search_fields = (
        'user',
        'recipe',
        'add_date'
    )


admin.site.register(Ingredient, IngedientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)

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
    extra = 1


class TagRecipeInLine(admin.TabularInline):
    model = TagRecipe
    extra = 1


class RecipeAdmin(admin.ModelAdmin):
    inlines = (IngredientRecipeInLine, TagRecipeInLine,)
    list_display = (
        'id',
        'author',
        'name',
        'image',
        'text',
        'cooking_time',
    )
    search_fields = (
        'name',
        'author',
        'cooking_time',
    )


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


class ShopiingCartAdmin(admin.ModelAdmin):
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
admin.site.register(ShoppingCart, ShopiingCartAdmin)

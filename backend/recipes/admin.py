from django.contrib import admin

from .models import IngredientRecipe, Recipe


class IngredientInline(admin.TabularInline):
    model = IngredientRecipe
    extra = 1
    min_num = 1
    fields = ('ingredient', 'amount')
    required = ('ingredient', 'amount')


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'author',
        'get_favorite_recipe_count'
    )
    inlines = [IngredientInline]
    list_filter = (
        'author',
        'name',
        'tags',
    )
    filter_horizontal = (
        'tags',
    )

    @admin.display(description='Добавлено в избранное')
    def get_favorite_recipe_count(self, obj):
        return obj.favorite_recipe.count()


@admin.register(IngredientRecipe)
class IngredientRecipeAdmin(admin.ModelAdmin):
    list_display = (
        'recipe',
        'ingredient',
        'amount'
    )

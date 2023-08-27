from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from favorites.models import Favorite
from ingredients.models import Ingredient
from shoppingcarts.models import ShoppingCart
from tags.models import Tag
from recipes.models import IngredientRecipe, Recipe
from ..services import Base64ImageField
from ..tags.serializers import TagSerializer
from ..users.serializers import CustomUserSerializer


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = serializers.SerializerMethodField(
        method_name='get_ingredients'
    )
    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(read_only=True)
    image = Base64ImageField(
        max_length=None, use_url=True,
    )
    is_favorited = serializers.SerializerMethodField(
        method_name='get_is_favorited'
    )
    is_in_shopping_cart = serializers.SerializerMethodField(
        method_name='get_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        )

    def get_ingredients(self, obj):
        recipe = obj
        return (
            recipe.ingredients.values(
                'id',
                'name',
                'measurement_unit',
                amount=F('ingredientrecipe__amount')
            )
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and Favorite.objects.filter(
            user=user,
            recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and ShoppingCart.objects.filter(
            user=user,
            recipe=obj
        ).exists()


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = Ingredient
        fields = ('id', 'amount')


class RecipeCreateSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    ingredients = IngredientRecipeSerializer(many=True)
    image = Base64ImageField()
    cooking_time = serializers.IntegerField()

    def _create_ingredients(self, ingredients, recipe):
        IngredientRecipe.objects.bulk_create(
            [
                IngredientRecipe(
                    ingredient=ingredient["id"],
                    recipe=recipe,
                    amount=ingredient["amount"],
                )
                for ingredient in ingredients
            ]
        )

    def validate_ingredients(self, value):
        if not value:
            raise ValidationError(
                'Количество ингредиентов должно быть больше 0'
            )
        ingredients = [item['id'] for item in value]
        ingredients_roster = set()
        for ingredient in ingredients:
            if ingredient in ingredients_roster:
                raise ValidationError(
                    'Ингредиенты не должны дублироваться')
            ingredients_roster.add(ingredient)
        return value

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        recipe.save()
        self._create_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        instance.tags.set(tags)

        ingredients = validated_data.pop('ingredients', None)
        instance.ingredients.clear()

        ingredient_roster = set()
        for ingredient in ingredients:
            amount = ingredient['amount']
            ingredient_id = ingredient['id']
            ingredient_roster.add(ingredient_id)

            ingredient = get_object_or_404(Ingredient, pk=ingredient['id'])

            IngredientRecipe.objects.update_or_create(
                recipe=instance,
                ingredient=ingredient,
                defaults={'amount': amount}
            )

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        serializer = RecipeSerializer(
            instance,
            context={'request': self.context.get('request')}
        )

        return serializer.data

    class Meta:
        model = Recipe
        fields = (
            'id',
            'ingredients',
            'tags',
            'author',
            'image',
            'name',
            'text',
            'cooking_time',
        )

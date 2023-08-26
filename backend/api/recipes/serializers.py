from django.db.models import F
from django.shortcuts import get_object_or_404
from favorites.models import Favorite
from ingredients.models import Ingredient
from recipes.models import IngredientRecipe, Recipe
from rest_framework import serializers
from shoppingcarts.models import ShoppingCart
from tags.models import Tag

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
        return ShoppingCart.objects.filter(
            user=user,
            recipe=obj
        ).exists() if user.is_authenticated else False


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

    def validate(self, data):
        cooking_time = data.get('cooking_time')

        if cooking_time <= 0:
            raise serializers.ValidationError(
                'Время приготовления должно быть больше 0'
            )

        ingredients_data = data.get('ingredients')
        ingredient_ids = set()
        for ingredient_data in ingredients_data:
            amount = ingredient_data.get('amount')
            if amount <= 0:
                raise serializers.ValidationError(
                    'Количество ингредиентов должно быть больше 0'
                )
            ingredient_id = ingredient_data.get('id')
            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(
                    'Ингредиенты не должны дублироваться'
                )
            ingredient_ids.add(ingredient_id)
            try:
                Ingredient.objects.get(id=ingredient_id)
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    'Ингредиента с указанным идентификатором '
                    'не существует в базе данных'
                )

        if not data.get('tags'):
            raise serializers.ValidationError(
                'Необходимо указать хотя бы один тег'
            )

        if not data.get('ingredients'):
            raise serializers.ValidationError(
                'Необходимо указать хотя бы один ингредиент'
            )

        return data

    def create(self, validated_data):
        author = self.context.get('request').user
        tags = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.tags.set(tags)
        for ingredient_data in ingredients_data:
            ingredient = Ingredient.objects.get(id=ingredient_data.get('id'))
            amount = ingredient_data.get('amount')
            IngredientRecipe.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=amount)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        instance.tags.set(tags)

        ingredients = validated_data.pop('ingredients', None)
        instance.ingredients.clear()

        ingredient_ids = set()
        for ingredient in ingredients:
            amount = ingredient['amount']
            ingredient_id = ingredient['id']
            ingredient_ids.add(ingredient_id)

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

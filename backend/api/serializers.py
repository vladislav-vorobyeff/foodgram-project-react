from django.db import transaction
from djoser.serializers import UserCreateSerializer, UserSerializer
from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework.serializers import (CharField, IntegerField,
                                        ModelSerializer,
                                        PrimaryKeyRelatedField, ReadOnlyField,
                                        SerializerMethodField, ValidationError)
from users.models import CustomUser, Subscriptions

from .services import Base64ImageField


class IngredientSerializer(ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientRecipeSerializer(ModelSerializer):
    id = ReadOnlyField(source='ingredient.id')
    name = ReadOnlyField(source='ingredient.name')
    measurement_unit = ReadOnlyField(source='ingredient.measurement_unit')

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class ShortRecipeSerializer(ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class IngredientAddSerializer(ModelSerializer):
    id = PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = IntegerField()

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class RecipeGetSerializer(ModelSerializer):
    tags = TagSerializer(many=True)
    author = UserSerializer(many=False)
    ingredients = IngredientRecipeSerializer(
        many=True,
        source='ingredientrecipes'
    )
    is_favorited = SerializerMethodField()
    is_in_shopping_cart = SerializerMethodField()

    class Meta:
        model = Recipe
        fields = '__all__'

    def get_is_favorited(self, obj):
        return (self.context.get('request').user.is_authenticated
                and Favorite.objects.filter(
                    user=self.context.get('request').user,
                    recipe=obj
        ).exists())

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return (
            request.user.is_authenticated
            and ShoppingCart.objects.filter(
                user=request.user,
                recipe__id=obj.id
            ).exists()
        )


class RecipeSerializer(ModelSerializer):
    tags = PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    ingredients = IngredientAddSerializer(many=True)
    image = Base64ImageField(max_length=None)

    class Meta:
        model = Recipe
        fields = (
            'tags',
            'name',
            'ingredients',
            'image',
            'text',
            'cooking_time'
        )

    def to_representation(self, instance):
        serializer = RecipeGetSerializer(instance)
        return serializer.data

    @transaction.atomic
    def _create_ingredients(self, ingredients, recipe):
        IngredientRecipe.objects.bulk_create(
            [IngredientRecipe(
                ingredient_id=ingredient['id'],
                recipe=recipe,
                amount=ingredient['amount']
            ) for ingredient in ingredients]
        )

    def validate(self, data):
        ingredients = data.get('ingredients')
        for ingredient in ingredients:
            if int(ingredient['amount']) <= 0:
                raise ValidationError(
                    'Нужен минимум 1 ингридиент'
                )
            if ingredients.count(ingredient) > 1:
                raise ValidationError(
                    'Ингридиент уже добавлен'
                )
        return data

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self._create_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.ingredients.clear()
        self._create_ingredients(ingredients, instance)
        instance.tags.clear()
        instance.tags.set(tags)
        return super().update(instance, validated_data)


class UserListSerializer(UserSerializer):
    is_subscribed = SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        return (self.context.get('request').user.is_authenticated
                and Subscriptions.objects.filter(
                    user=self.context.get('request').user,
                    author=obj
        ).exists())


class UserCreateSerializer(UserCreateSerializer):
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name', 'password')
        required_fields = (
            'email',
            'username',
            'first_name',
            'last_name',
            'password'
        )


class SubscribeSerializer(ModelSerializer):
    email = CharField(
        source='author.email',
        read_only=True)
    id = IntegerField(
        source='author.id',
        read_only=True)
    username = CharField(
        source='author.username',
        read_only=True)
    first_name = CharField(
        source='author.first_name',
        read_only=True)
    last_name = CharField(
        source='author.last_name',
        read_only=True)
    recipes = SerializerMethodField()
    is_subscribed = SerializerMethodField()
    recipes_count = ReadOnlyField(
        source='author.recipe.count')

    class Meta:
        model = Subscriptions
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes', 'recipes_count',)

    def validate(self, data):
        user = self.context.get('request').user
        author = self.context.get('author_id')
        if user.id == int(author):
            raise ValidationError(
                'Нельзя подписаться на самого себя'
            )
        if Subscriptions.objects.filter(user=user, author=author).exists():
            raise ValidationError(
                'Вы уже подписаны на данного пользователя'
            )
        return data

    def get_recipes(self, obj):
        try:
            recipe_limit = int(
                self.context.get('request').query_params['recipes_limit']
            )
            queryset = Recipe.objects.filter(author=obj.author)[:recipe_limit]
        except TypeError:
            queryset = Recipe.objects.filter(author=obj.author)
        serializer = ShortRecipeSerializer(queryset, read_only=True, many=True)

        return serializer.data

    def get_is_subscribed(self, obj):
        return Subscriptions.objects.filter(
            user=obj.user,
            author=obj.author
        ).exists()

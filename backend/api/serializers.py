from djoser.serializers import UserSerializer
from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework.serializers import (ImageField, IntegerField,
                                        ModelSerializer,
                                        PrimaryKeyRelatedField, ReadOnlyField,
                                        SerializerMethodField, ValidationError)
from rest_framework.validators import UniqueTogetherValidator
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
        request = self.context.get('request')
        return (request.user.is_authenticated
                and obj.favorite.filter(user=request.user).exists())

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

    def _create_ingredients(self, ingredients, recipe):
        ingredients_accum = [
            IngredientRecipe(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            ) for ingredient in ingredients
        ]
        IngredientRecipe.objects.bulk_create(ingredients_accum)

    def validate(self, data):
        ingredients = data.get('ingredients')
        for ingredient in ingredients:
            if int(ingredient['amount']) <= 0:
                raise ValidationError({
                    'ingredients': ('Число игредиентов должно быть больше 0')
                })
            if ingredients.count(ingredient) > 1:
                raise ValidationError({
                    'ingredients': ('Ингридиент повторяется')
                })
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


class UserSerializer(UserSerializer):
    is_subscribed = SerializerMethodField(
        method_name='get_is_subscribed'
    )

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'username',
            'password',
            'email',
            'first_name',
            'last_name',
            'is_subscribed'
        )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Subscriptions.objects.filter(
            user=request.user, author=obj
        ).exists()


class SubscriptionsSerializer(ModelSerializer):
    is_subscribed = SerializerMethodField()
    recipe = SerializerMethodField()
    recipes_count = SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipe',
            'recipes_count'
        )

    def get_is_subscribed(self, obj):
        return Subscriptions.objects.filter(
            user=obj.user,
            author=obj.author
        ).exists()

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

    def get_recipes_count(self, obj):
        return obj.recipe.count()


class SubscribeListSerializer(ModelSerializer):

    class Meta:
        model = Subscriptions
        fileds = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Subscriptions.objects.all(),
                fields=['user', 'author'],
            )
        ]

    def to_representation(self, instance):
        return SubscriptionsSerializer(instance.author, context={
            'request': self.context.get('request')
        }).data


class FavoriteSerializer(ModelSerializer):
    id = PrimaryKeyRelatedField(source="recipe", read_only=True)
    name = ReadOnlyField(source="recipe.name")
    image = ImageField(source="recipe.image", read_only=True)
    cooking_time = IntegerField(source="recipe.cooking_time", read_only=True)

    class Meta:
        model = Favorite
        fields = ("id", "name", "image", "cooking_time")

    def validate(self, data):
        user = data['user']
        if user.favorites.filter(recipe=data['recipe']).exists():
            raise ValidationError(
                'Рецепт уже добавлен в избранное.'
            )
        return data

    def to_representation(self, instance):
        return ShortRecipeSerializer(
            instance.recipe,
            context={'request': self.context.get('request')}
        ).data


class ShoppingCartSerializer(ModelSerializer):
    id = PrimaryKeyRelatedField(source="recipe", read_only=True)
    name = ReadOnlyField(source="recipe.name")
    image = ImageField(source="recipe.image", read_only=True)
    cooking_time = IntegerField(source="recipe.cooking_time", read_only=True)

    class Meta:
        model = ShoppingCart
        fields = (
            "id",
            "name",
            "image",
            "cooking_time",
        )

    def validate(self, data):
        user = data['user']
        if user.shopping_list.filter(recipe=data['recipe']).exists():
            raise ValidationError(
                'Рецепт уже добавлен в корзину'
            )
        return data

    def to_representation(self, instance):
        return ShortRecipeSerializer(
            instance.recipe,
            context={'request': self.context.get('request')}
        ).data

from djoser.serializers import UserSerializer
from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework import exceptions, status
from rest_framework.serializers import (IntegerField, ModelSerializer,
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
        request = self.context.get('request')
        return (
            request is not None
            and not request.user.is_anonymous
            and request.user.is_authenticated
            and Favorite.objects.filter(
                user=request.user,
                recipe__id=obj.id
            ).exists()
        )

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
        ingredient_list = [
            IngredientRecipe(recipe=recipe,
                             ingredient=ingredient['id'],
                             amount=ingredient['amount'])
            for ingredient in ingredients
        ]
        IngredientRecipe.objects.bulk_create(ingredient_list)

    def validate(self, value):
        ingredients = self.initial_data.get('ingredients')
        if len(ingredients) <= 0:
            raise ValidationError(
                {'ingredients': 'Количество '
                 'ингредиентов не может быть меньше 1'}
            )
        ingredients_list = []
        for item in ingredients:
            if item['id'] in ingredients_list:
                raise ValidationError(
                    {'ingredients': 'Ингредиенты не могут повторяться'}
                )
            ingredients_list.append(item['id'])
            if int(item['amount']) <= 0:
                raise ValidationError(
                    {'amount': 'Количество '
                     'ингредиентов не может быть меньше 1}'}
                )
        return value

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.ingredients.clear()
        self.create_ingredients(ingredients, instance)
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
        user = CustomUser.objects.create_user(
            **validated_data
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Subscriptions.objects.filter(
            user=request.user, author=obj
        ).exists()


class UsersSerializer(ModelSerializer):
    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'username',
                  'first_name', 'last_name', 'is_subscribed',)

    def get_is_subscribed(self, author):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and request.user.follower.filter(author=author).exists())


class SubscriptionsSerializer(UsersSerializer):
    recipes = SerializerMethodField(read_only=True)
    recipes_count = SerializerMethodField(read_only=True)

    class Meta(UsersSerializer.Meta):
        fields = UsersSerializer.Meta.fields + ('recipes', 'recipes_count',)
        read_only_fields = ('email', 'username', 'last_name', 'first_name',)

    def validate(self, data):
        author = self.instance
        user = self.context.get('request').user
        if Subscriptions.objects.filter(user=user, author=author).exists():
            raise ValidationError(
                detail='Вы уже подписаны на этого пользователя',
                code=status.HTTP_400_BAD_REQUEST
            )
        if user == author:
            raise exceptions.ValidationError(
                detail='Вы не можете подписаться на самого себя',
                code=status.HTTP_400_BAD_REQUEST
            )
        return data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

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

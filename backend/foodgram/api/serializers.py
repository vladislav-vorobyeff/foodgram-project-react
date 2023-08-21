from base64 import b64decode

from django.core.files.base import ContentFile
from djoser.serializers import UserSerializer
from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework.serializers import (ImageField, IntegerField,
                                        ModelSerializer,
                                        PrimaryKeyRelatedField, ReadOnlyField,
                                        SerializerMethodField, ValidationError)
from users.models import CustomUser, Subscriptions


class Base64ImageField(ImageField):

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


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


class AddIngredientSerializer(ModelSerializer):
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
        if request is None or request.user.is_anonymous:
            return False
        return (
            request.user.is_authenticated
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
    ingredients = AddIngredientSerializer(many=True)
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

    def create_ingredients(self, ingredients, recipe):
        for ingredient in ingredients:
            IngredientRecipe.objects.get_or_create(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            )

    def validate(self, data):
        ingredients = self.initial_data.get('ingredients')
        ingredients_list = [ingredient['id'] for ingredient in ingredients]
        amount_list = [int(ingredient['amount']) for ingredient in ingredients]
        if len(ingredients_list) != len(set(ingredients_list)):
            raise ValidationError(
                'Каждый ингредиент может быть добавлен не более 1 раза'
            )
        for amount in amount_list:
            if amount <= 0:
                raise ValidationError(
                    'Количество должно быть больше нуля'
                )
        return data

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        recipe.save()
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
        user = CustomUser(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
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


class SubscriptionsSerializer(ModelSerializer):
    username = ReadOnlyField(source='author.username')
    email = ReadOnlyField(source='author.email')
    first_name = ReadOnlyField(source='author.first_name')
    last_name = ReadOnlyField(source='author.last_name')
    id = ReadOnlyField(source='author.id')
    is_subscribed = SerializerMethodField()
    recipes = SerializerMethodField()
    recipes_count = IntegerField(
        source='author.recipes.count',
        read_only=True
    )

    class Meta:
        model = Subscriptions
        fields = (
            'id', 'username', 'email', 'first_name',
            'last_name', 'is_subscribed',
            'recipes', 'recipes_count'
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
        except Exception:
            queryset = Recipe.objects.filter(author=obj.author)
        serializer = ShortRecipeSerializer(queryset, read_only=True, many=True)

        return serializer.data

    def get_recipes_count(self, obj):
        return obj.author.recipes.count()

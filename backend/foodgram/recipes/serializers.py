from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from .fields import Base64ImageField
from .models import (Cart, Favourite, Follow,
                     Ingredient, Recipe, RecipeIngredient, Tag)
from users.serializers import UserSubscribedSerializer


User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов"""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')

    def validate_color(self, value):
        return value.upper()


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов"""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')
        read_only_fields = ('name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте"""
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all()
    )
    name = serializers.SlugRelatedField(
        slug_field='name',
        source='ingredient',
        read_only=True
    )
    measurement_unit = serializers.SlugRelatedField(
        slug_field='measurement_unit',
        source='ingredient',
        read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class GetRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для получения рецептов"""
    author = UserSubscribedSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        read_only=True,
        source='ingredient'
    )
    tags = TagSerializer(many=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

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
            'cooking_time',
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and Favourite.objects.filter(
            user=user,
            recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and Cart.objects.filter(
            user=user,
            recipe=obj
        ).exists()

class RecipeSerializer(GetRecipeSerializer):
    """Сериализатор для создания и изменения рецептов"""
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='ingredient'
    )
    image = Base64ImageField()
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
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
            'cooking_time',
        )
        read_only_fields = ('image',)

    def to_representation(self, instance):
        return super().to_representation(instance)

    def validate(self, data):
        tags = data['tags']
        if not isinstance(tags, list):
            raise serializers.ValidationError(
                {'error': 'Тэги должны быть в виде списка'}
            )
        for tag in tags:
            if not isinstance(tag, Tag):
                raise serializers.ValidationError(
                    {'error': 'Введите id тэгов'}
                )
        ingredients = data['ingredient']
        if not isinstance(ingredients, list):
            raise serializers.ValidationError(
                {'error': 'Ингредиенты должны быть в виде списка'}
            )
        if not len(set(
            [param['ingredient'] for param in ingredients]
        )) == len(ingredients):
            raise serializers.ValidationError(
                {'error': 'Ингредиенты не должны дублироваться'}
            )
        for unit in ingredients:
            if not isinstance(unit, dict):
                raise serializers.ValidationError(
                    {'error': ('Ингредиент должен быть '
                               'словарём с ключами "id" и "amount"')}
                )
            amount = unit['amount']
            if amount < 1:
                raise serializers.ValidationError(
                    {'error': ('Количество ингредиента должно '
                                   'быть положительным числом')}
                )
        if not data['cooking_time']:
            raise serializers.ValidationError(
                {
                    'error': ('Время приготовления должно '
                              'быть положительным числом')}
            )
        return data
    
    @staticmethod
    def add_ingredients(recipe, ingredients):
        RecipeIngredient.objects.bulk_create(
            [RecipeIngredient(
                recipe=recipe,
                ingredient=param['ingredient'],
                amount=param['amount']
             ) for param in ingredients
            ]
        )

    def create(self, validated_data):
        recipe = Recipe.objects.create(
            author=validated_data['author'],
            name=validated_data['name'],
            text=validated_data['text'],
            image=validated_data['image'],
            cooking_time=validated_data['cooking_time'],
        )
        tags = validated_data.get('tags')
        recipe.tags.set(
            Tag.objects.filter(pk__in=[tag.pk for tag in tags])
        )
        ingredients = validated_data.get('ingredient')
        self.add_ingredients(recipe, ingredients)
        return recipe

    def update(self, recipe, validated_data):
        recipe.name = validated_data.get('name', recipe.name)
        recipe.text = validated_data.get('text', recipe.text)
        recipe.image = validated_data.get('image', recipe.image)
        recipe.cooking_time = validated_data.get(
            'cooking_time',
            recipe.cooking_time
        )
        recipe.tags.clear()
        tags = validated_data.get('tags')
        recipe.tags.set(
            Tag.objects.filter(pk__in=[tag.pk for tag in tags])
        )
        recipe.ingredients.clear()
        ingredients = validated_data.get('ingredient')
        self.add_ingredients(recipe, ingredients)
        recipe.save()
        return recipe


class FavouriteCartRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор полей избранных рецептов и покупок"""

    class Meta(RecipeSerializer.Meta):
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class FavouriteRecipeSerializer(FavouriteCartRecipeSerializer):
    """Сериализатор для избранных"""
    def create(self, validated_data):
        user = validated_data['user']
        recipe = validated_data['recipe']
        Favourite.objects.create(user=user, recipe=recipe)
        return recipe

    def validate(self, data):
        user = self.context['request'].user
        pk = self.context['request'].parser_context['kwargs']['pk']
        recipe = get_object_or_404(Recipe, pk=pk)
        if Favourite.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                {'error': 'Рецепт уже добавлен в избранное'}
            )
        return data


class CartRecipeSerializer(FavouriteCartRecipeSerializer):
    """Сериализатор для покупок"""
    def create(self, validated_data):
        user = validated_data['user']
        recipe = validated_data['recipe']
        Cart.objects.create(user=user, recipe=recipe)
        return recipe

    def validate(self, data):
        user = self.context['request'].user
        pk = self.context['request'].parser_context['kwargs']['pk']
        recipe = get_object_or_404(Recipe, pk=pk)
        if Cart.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                {'error': 'Рецепт уже в корзине'}
            )
        return data


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор для подписок"""
    recipes = FavouriteCartRecipeSerializer(many=True, read_only=True)
    is_subscribed = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )
        read_only_fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )

    def validate(self, data):
        if self.context['request'].method == 'POST':
            follower = self.context['request'].user
            following_pk = self.context[
                'request'
            ].parser_context['kwargs'].get('pk')
            following = get_object_or_404(User, pk=following_pk)
            if follower == following:
                raise serializers.ValidationError(
                    {'error': 'Нельзя подписаться на самого себя'}
                )
            if Follow.objects.filter(
                follower=follower, following=following
            ).exists():
                raise serializers.ValidationError(
                    {'error': 'Вы уже подписаны на этого пользователя'}
                )
        return data

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and Follow.objects.filter(
            follower=user,
            following=obj
        ).exists()

    def get_recipes_count(self, obj):
        return obj.recipes.all().count()

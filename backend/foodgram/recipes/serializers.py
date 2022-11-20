from base64 import b64decode

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from recipes.models import (Cart, Favourite, Follow,
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


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(b64decode(imgstr), name='image.'+ext)
        return super().to_internal_value(data)


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для рецептов"""
    author = UserSubscribedSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    image = Base64ImageField()
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
        read_only_fields = ('author', 'image')

    def validate(self, data):
        raw_data = self.initial_data
        if 'tags' in raw_data:
            tags = raw_data['tags']
            if not isinstance(tags, list):
                raise serializers.ValidationError(
                    {'error': 'Тэги должны быть в виде списка'}
                )
            for tag in tags:
                if not isinstance(tag, int):
                    raise serializers.ValidationError(
                        {'error': 'Введите id тэгов'}
                    )
        if 'ingredients' in raw_data:
            ingredients = raw_data['ingredients']
            if not isinstance(ingredients, list):
                raise serializers.ValidationError(
                    {'error': 'Ингредиенты должны быть в виде списка'}
                )
            for unit in ingredients:
                if not (isinstance(unit, dict) and
                        'id' in unit and 'amount' in unit):
                    raise serializers.ValidationError(
                        {'error': ('Ингредиент должен быть '
                                   'словарём с ключами "id" и "amount"')}
                    )
                amount = int(unit['amount'])
                if amount < 1:
                    raise serializers.ValidationError(
                        {'error': ('Количество ингредиента должно '
                                   'быть положительным числом')}
                    )
        if 'cooking_time' in raw_data and not raw_data['cooking_time']:
            raise serializers.ValidationError(
                {
                    'error': ('Время приготовления должно '
                              'быть положительным числом')}
            )
        return data

    def create(self, validated_data):
        recipe = Recipe.objects.create(**validated_data)
        recipe.save()
        tags_pk = self.initial_data.get('tags')
        tags = Tag.objects.filter(pk__in=tags_pk)
        recipe.tags.set(tags)
        ingredients_params = self.initial_data.get('ingredients')
        for param in ingredients_params:
            ingredient = get_object_or_404(
                Ingredient,
                pk=param['id']
            )
            RecipeIngredient.objects.create(
                ingredient=ingredient,
                recipe=recipe,
                amount=param['amount']
            )
        return recipe

    def update(self, recipe, validated_data):
        raw_data = self.initial_data
        if 'tags' in raw_data:
            recipe.tags.clear()
            tags = Tag.objects.filter(id__in=raw_data['tags'])
            recipe.tags.set(tags)
        if 'ingredients' in raw_data:
            recipe.ingredients.clear()
            for param in raw_data['ingredients']:
                ingredient = get_object_or_404(
                    Ingredient,
                    id=param['id']
                )
                RecipeIngredient.objects.create(
                    ingredient=ingredient,
                    recipe=recipe,
                    amount=param['amount']
                )
        super().update(recipe, validated_data)
        return recipe

    def get_ingredients(self, obj):
        data = []
        for ingredient in obj.ingredients.all():
            unit = get_object_or_404(
                RecipeIngredient,
                recipe=obj,
                ingredient=ingredient)
            data.append(
                dict(
                    id=ingredient.id,
                    name=ingredient.name,
                    measurement_unit=ingredient.measurement_unit,
                    amount=unit.amount
                )
            )
        return data

    def get_is_favorited(self, obj):
        return Favourite.objects.filter(
            user=self.context['request'].user,
            recipe=obj,
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        return Cart.objects.filter(
            user=self.context['request'].user,
            recipe=obj
        ).exists()


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
        return len(obj.recipes.all())

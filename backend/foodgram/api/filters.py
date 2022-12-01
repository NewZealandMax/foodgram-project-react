from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe, Tag


class IngredientFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ['name']


class RecipeFilter(filters.FilterSet):
    tags = filters.CharFilter(field_name='tags__slug', method='tags_filter')
    is_favorited = filters.NumberFilter(method='favourites')
    is_in_shopping_cart = filters.NumberFilter(method='cart')

    class Meta:
        model = Recipe
        fields = ['author', 'tags', 'is_favorited', 'is_in_shopping_cart']

    def favourites(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated and value == 1:
            queryset = queryset.filter(users__user=user)
        return queryset

    def cart(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated and value == 1:
            queryset = queryset.filter(consumers__user=user)
        return queryset

    def tags_filter(self, queryset, name, value):
        tags = self.request.query_params.getlist('tags') 
        return queryset.filter(tags__slug__in=tags).distinct()

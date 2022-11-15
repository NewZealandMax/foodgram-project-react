import django_filters

from .models import Recipe


class RecipeFilter(django_filters.FilterSet):
    is_favorited = django_filters.NumberFilter(name='author__favourites')
    is_in_shopping_cart = django_filters.NumberFilter(name='author__cart')

    class Meta:
        model = Recipe
        fields = ['author', 'tags']

from django.contrib import admin
from .models import Cart, Favourite, Follow, Ingredient, Recipe, Tag


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    list_filter = ('name',)
    search_fields = ('name',)


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'favorites')
    list_filter = ('author', 'name', 'tags__name')

    def favorites(self, obj):
        return len(obj.users.all())


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug')


class FollowAdmin(admin.ModelAdmin):
    list_display = ('pk', 'follower', 'following')


class CartAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'recipe')


class FavouriteAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'recipe')


admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Follow, FollowAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Favourite, FavouriteAdmin)

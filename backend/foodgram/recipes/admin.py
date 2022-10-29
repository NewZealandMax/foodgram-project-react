from django.contrib import admin

from .models import Follow, Ingredient, Recipe, Tag


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    list_filter = ('name',)


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author')
    list_filter = ('author', 'name', 'tags')
    # общее число добавлений в избранное


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug')


class FollowAdmin(admin.ModelAdmin):
    list_display = ('pk', 'follower', 'following')


admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Follow, FollowAdmin)

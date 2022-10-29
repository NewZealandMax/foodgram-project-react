import io

from django.contrib.auth import get_user_model
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from recipes.models import (Cart, Favourite, Follow, Ingredient,
                            Recipe, RecipeIngredient, Tag)
from recipes.serializers import (FavouriteCartRecipeSerializer,
                                 FollowSerializer, IngredientSerializer,
                                 RecipeSerializer, TagSerializer)
from users.serializers import (UserSerializer, UserSetPasswordSerializer,
                               UserSubscribedSerializer)
from .permissions import RecipePermission, UserPermission


User = get_user_model()


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    #permission_classes = (RecipePermission,)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('author',)

    def get_queryset(self):
        print('Получаю список рецептов')
        queryset = Recipe.objects.all()
        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited is not None:
            favourite = Favourite.objects.filter(user=self.request.user)
            queryset = Recipe.objects.filter(users__in=favourite)
        is_in_shopping_cart = self.request.query_params.get('is_in_shopping_cart')
        if is_in_shopping_cart is not None:
            shopping_cart = Cart.objects.filter(user=self.request.user)
            queryset = Recipe.objects.filter(consumers__in=shopping_cart)
        tags = self.request.query_params.getlist('tags')
        if tags is not None:
            queryset = Recipe.objects.filter(tags__slug__in=tags).distinct()
        print(queryset)
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        super().perform_create(serializer)
    
    def perform_update(self, serializer):
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        super().perform_update(serializer)

    @action(methods=['POST', 'DELETE'], detail=True,
            permission_classes=[IsAuthenticated])
    def favorite(self, request, *args, **kwargs):
        print(self.permission_classes)
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        method = request.parser_context['request'].method
        if method == 'POST':
            serializer = FavouriteCartRecipeSerializer(
                recipe,
                data=request.data,
                context={'request': request}
            )
            if serializer.is_valid():
                Favourite.objects.create(user=request.user, recipe=recipe)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            get_object_or_404(
                Favourite,
                user=request.user,
                recipe=recipe
            ).delete()
            return Response({}, status=status.HTTP_204_NO_CONTENT)

    @action(methods=['POST', 'DELETE'], detail=True, permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, *args, **kwargs):
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        method = request.parser_context['request'].method
        if method == 'POST':
            serializer = FavouriteCartRecipeSerializer(
                recipe,
                data=request.data,
                context={'request': request}
            )
            if serializer.is_valid():
                Cart.objects.create(user=request.user, recipe=recipe)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            get_object_or_404(
                Cart,
                user=request.user,
                recipe=recipe
            ).delete()
            return Response({}, status=status.HTTP_204_NO_CONTENT)
    
    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request, *args, **kwargs):
        """Формирует pdf-файл со списком покупок"""
        buffer = io.BytesIO()
        pdfmetrics.registerFont(TTFont('TimesNewRoman', 'timesnewroman.ttf'))
        file = canvas.Canvas(buffer)
        file.setFont('TimesNewRoman', 14)
        file.drawString(200, 800, f'Список покупок пользователя {request.user.username}')
        goods = dict()
        for cart_unit in request.user.cart.all():
            for ingredient in cart_unit.recipe.ingredients.all():
                amount = get_object_or_404(
                    RecipeIngredient,
                    recipe=cart_unit.recipe,
                    ingredient=ingredient
                ).amount
                goods[ingredient.name] = goods.get(ingredient.name, 0) + amount
        left = 50
        bottom = 750
        for good, amount in goods.items():
            measure = get_object_or_404(Ingredient, name=good).measurement_unit
            file.drawString(left, bottom, f'{good} ({measure}) - {amount}')
            bottom -= 20
        file.showPage()
        file.save()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename='recipe_list.pdf')


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSubscribedSerializer
    permission_classes = [UserPermission]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserSerializer
        return UserSubscribedSerializer

    def get_object(self):
        user = self.request.user
        pk = self.kwargs['pk']
        if user.is_authenticated:
            if pk == 'me':
                return get_object_or_404(User, pk=user.pk)
            else:
                return get_object_or_404(User, pk=pk)
        raise NotAuthenticated

    @action(methods=['POST'], detail=False,
            permission_classes=[IsAuthenticated], serializer_class=UserSetPasswordSerializer)
    def set_password(self, request, *args, **kwargs):
        serializer = UserSetPasswordSerializer(User, request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(self.request.data['new_password'])
            user.save()
            return Response({}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request, *args, **kwargs):
        user = request.user
        queryset = User.objects.filter(followers__follower=user)
        page = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            page,
            context={'request': request},
            many=True
        )
        return self.get_paginated_response(serializer.data)
    
    @action(methods=['POST', 'DELETE'], detail=True, permission_classes=[IsAuthenticated])
    def subscribe(self, request, *args, **kwargs):
        following = get_object_or_404(User, pk=kwargs['pk'])
        method = request.parser_context['request'].method
        if method == 'POST':
            serializer = FollowSerializer(
                following,
                data=request.data,
                context={'request': request}
            )
            if serializer.is_valid():
                Follow.objects.create(follower=request.user, following=following)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            get_object_or_404(
                Follow,
                follower=request.user,
                following=following
            ).delete()
            return Response({}, status=status.HTTP_204_NO_CONTENT)

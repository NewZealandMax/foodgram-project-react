import io

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .permissions import RecipePermission
from recipes.models import (Cart, Favourite, Follow, Ingredient,
                            Recipe, Tag)
from recipes.serializers import (CartRecipeSerializer,
                                 FavouriteRecipeSerializer,
                                 FollowSerializer,
                                 GetRecipeSerializer,
                                 IngredientSerializer,
                                 RecipeSerializer, TagSerializer)
from users.serializers import (UserSerializer, UserSetPasswordSerializer,
                               UserSubscribedSerializer)


User = get_user_model()


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset для ингредиентов"""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """Viewset для рецептов"""
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (RecipePermission,)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return GetRecipeSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @staticmethod
    def add_remove_bookmark(request, model, serializer, **kwargs):
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        method = request.parser_context['request'].method
        if method == 'POST':
            serializer = serializer(
                recipe,
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            model.objects.create(user=request.user, recipe=recipe)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED)
        get_object_or_404(
            model,
            user=request.user,
            recipe=recipe
        ).delete()
        return Response({}, status=status.HTTP_204_NO_CONTENT)

    @action(methods=['POST', 'DELETE'], detail=True,
            permission_classes=[IsAuthenticated])
    def favorite(self, request, *args, **kwargs):
        """Добавляет и удаляет избранное"""
        return self.add_remove_bookmark(request,
                                        Favourite, 
                                        FavouriteRecipeSerializer,
                                        **kwargs
               )

    @action(methods=['POST', 'DELETE'],
            detail=True, permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, *args, **kwargs):
        """Добавляет и удаляет покупки"""
        return self.add_remove_bookmark(request,
                                        Cart, 
                                        CartRecipeSerializer,
                                        **kwargs
               )

    @action(methods=['GET'], detail=False,
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request, *args, **kwargs):
        """Формирует pdf-файл со списком покупок"""
        buffer = io.BytesIO()
        pdfmetrics.registerFont(TTFont('TimesNewRoman', 'timesnewroman.ttf'))
        file = canvas.Canvas(buffer)
        file.setFont('TimesNewRoman', 14)
        file.drawString(200, 800,
                        f'Список покупок пользователя {request.user.username}')
        left = 50
        bottom = 750
        for unit in request.user.cart.values(
            'recipe_id__ingredient__ingredient__name',
            'recipe_id__ingredient__ingredient__measurement_unit',
        ).annotate(Sum('recipe_id__ingredient__amount')):
            name = unit['recipe_id__ingredient__ingredient__name']
            measure = unit['recipe_id__ingredient__ingredient__measurement_unit']
            amount = unit['recipe_id__ingredient__amount__sum']
            file.drawString(left, bottom, f'{name} ({measure}) - {amount}')
            bottom -= 20
        file.showPage()
        file.save()
        buffer.seek(0)
        return FileResponse(
            buffer, as_attachment=True, filename='recipe_list.pdf')


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset для тегов"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class UserViewSet(viewsets.ModelViewSet):
    """Viewset для пользователей"""
    queryset = User.objects.all()
    serializer_class = UserSubscribedSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return UserSerializer
        return UserSubscribedSerializer

    def get_object(self):
        user = self.request.user
        pk = self.kwargs['pk']
        if pk == 'me':
            if user.is_authenticated:
                return get_object_or_404(User, pk=user.pk)
            raise NotAuthenticated
        return get_object_or_404(User, pk=pk)

    @action(methods=['POST'], detail=False,
            permission_classes=[IsAuthenticated],
            serializer_class=UserSetPasswordSerializer)
    def set_password(self, request, *args, **kwargs):
        """Изменяет пароль"""
        serializer = UserSetPasswordSerializer(
            User, request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(self.request.data['new_password'])
        user.save()
        return Response({}, status=status.HTTP_201_CREATED)

    @action(methods=['GET'], detail=False,
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request, *args, **kwargs):
        """Возвращает подписки"""
        user = request.user
        queryset = User.objects.filter(followers__follower=user)
        page = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            page,
            context={'request': request},
            many=True
        )
        return self.get_paginated_response(serializer.data)

    @action(methods=['POST', 'DELETE'],
            detail=True, permission_classes=[IsAuthenticated])
    def subscribe(self, request, *args, **kwargs):
        """Добавляет и удаляет подписки"""
        following = get_object_or_404(User, pk=kwargs['pk'])
        method = request.parser_context['request'].method
        if method == 'POST':
            serializer = FollowSerializer(
                following,
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            Follow.objects.create(
                follower=request.user, following=following
            )
            return Response(
                serializer.data, status=status.HTTP_201_CREATED
            )
        get_object_or_404(
            Follow,
            follower=request.user,
            following=following
        ).delete()
        return Response({}, status=status.HTTP_204_NO_CONTENT)

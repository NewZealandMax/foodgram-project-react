from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from recipes.models import Follow


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор формы регистрации пользователя"""
    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name')

    def create(self, validated_data):
        """Хеширует пароль при создании пользователя"""
        user = User.objects.create_user(**validated_data)
        user.set_password(self.initial_data['password'])
        user.save()
        return user


class UserSubscribedSerializer(UserSerializer):
    """Сериализатор сведений о пользователе"""
    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('is_subscribed',)

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and Follow.objects.filter(
            follower=user,
            following=obj
        ).exists()

class UserSetPasswordSerializer(UserSerializer):
    """Сериализатор формы смены пароля"""
    current_password = serializers.CharField()
    new_password = serializers.CharField()

    class Meta(UserSerializer.Meta):
        fields = ('new_password', 'current_password')

    def validate(self, data):
        """Проверка правильности пароля пользователя"""
        request = self.context['request']
        username = self.context['request'].user.username
        password = data['current_password']
        user = authenticate(request, username=username, password=password)
        if user is None:
            raise serializers.ValidationError({'error': 'Неверный пароль пользователя'})
        return data

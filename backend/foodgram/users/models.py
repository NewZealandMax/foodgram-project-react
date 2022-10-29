from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class FoodgramUser(AbstractUser):
    email = models.EmailField(
        max_length=254,
        unique=True,
        verbose_name='email'
    )
    username = models.CharField(
        max_length=150,
        validators=[RegexValidator(r'^[\w.@+-]+$')],
        unique=True,
        verbose_name='Псевдоним'
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Фамилия',
    )
    password = models.CharField(
        max_length=150,
        verbose_name='Пароль'
    )

    class Meta:
        ordering = ['-id']

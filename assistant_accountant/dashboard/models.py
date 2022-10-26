from django.db import models
from django.contrib.auth import get_user_model

from core.models import CreateModel

User = get_user_model()


class YandexDirectToken(CreateModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='yandex_direct_tokens'
    )
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_in = models.IntegerField()

    def __str__(self):
        return self.user.username


class VkAdsToken(CreateModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vk_ads_tokens'
    )
    access_token = models.TextField()
    expires_in = models.IntegerField()

    def __str__(self):
        return self.user.username


class MyTargetToken(CreateModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='my_target_tokens'
    )
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_in = models.IntegerField()

    def __str__(self):
        return self.user.username

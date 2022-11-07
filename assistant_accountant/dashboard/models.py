from django.core.validators import MinValueValidator
from django.db import models
from django.contrib.auth import get_user_model

from core.models import CreateModel

User = get_user_model()
YANDEX_DIRECT = 'yandex_direct'
MY_TARGET = 'my_target'
VK_ADS = 'vk_ads'
DEFAULT_MAX_LENGTH = 256


class Token(CreateModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    expires_in = models.IntegerField()
    source = models.ForeignKey('Source', on_delete=models.CASCADE)

    class Meta:
        db_table = 'tokens'
        ordering = ['user', 'source']
        default_related_name = 'tokens'

    def __str__(self):
        return f'{self.source}/{self.user.username}'


class Source(models.Model):
    SOURCES = (
        (YANDEX_DIRECT, 'Яндекс Директ'),
        (MY_TARGET, 'myTarget'),
        (VK_ADS, 'VK ADS')
    )

    name = models.CharField(
        choices=SOURCES,
        max_length=DEFAULT_MAX_LENGTH,
        unique=True
    )

    class Meta:
        db_table = 'sources'
        ordering = ['name']

    def __str__(self):
        return self.name


class VkAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='vk_accounts')
    name = models.CharField(max_length=DEFAULT_MAX_LENGTH)
    account_id = models.IntegerField()

    class Meta:
        db_table = 'vk_accounts'
        ordering = ['user']

    def __str__(self):
        return self.name


class AgencyClient(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    client_id = models.IntegerField()
    name = models.CharField(max_length=DEFAULT_MAX_LENGTH)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    account = models.ForeignKey(VkAccount, on_delete=models.CASCADE,
                                blank=True, null=True)

    class Meta:
        db_table = 'agency_clients'
        default_related_name = 'agency_clients'
        ordering = ['user', 'source', 'name']

    def __str__(self):
        return self.name


class Campaign(models.Model):
    client = models.ForeignKey(AgencyClient, on_delete=models.CASCADE)
    name = models.CharField(max_length=DEFAULT_MAX_LENGTH)
    campaign_id = models.IntegerField()
    source = models.ForeignKey(Source, on_delete=models.CASCADE)

    class Meta:
        db_table = 'campaigns'
        ordering = ['client', 'source', 'name']
        default_related_name = 'campaigns'

    def __str__(self):
        return self.name


class BalanceHistory(models.Model):
    client = models.ForeignKey(AgencyClient, on_delete=models.CASCADE)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE,
                                 blank=True, null=True)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    amount = models.FloatField()
    date = models.DateField(auto_now_add=True)

    class Meta:
        db_table = 'balance_history'
        ordering = ['client', '-date', 'amount']
        default_related_name = 'balance_history'

    def __str__(self):
        return self.client.name


class StatisticByAgencyClient(models.Model):
    client = models.ForeignKey(AgencyClient, on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    cost = models.FloatField(validators=[MinValueValidator(0.0)])
    date = models.DateField()

    class Meta:
        db_table = 'statistic_by_agency_clients'
        ordering = ['client', 'source', '-date']
        default_related_name = 'statistic_by_agency_clients'

    def __str__(self):
        return self.date

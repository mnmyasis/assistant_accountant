from django.contrib import admin

from . import models

admin.site.register(models.Source)
admin.site.register(models.Campaign)

admin.site.empty_value_display = 'NONE'


@admin.register(models.Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('source', 'user', 'expires_in')
    list_filter = ('source',)


@admin.register(models.VkAccount)
class VkAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'account_id')
    list_filter = ('user',)


@admin.register(models.AgencyClient)
class AgencyClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'source', 'account', 'account_id')
    list_filter = ('source',)
    search_fields = ('name',)

    @admin.display(empty_value='NONE')
    def account_id(self, obj):
        if obj.account:
            return obj.account.account_id


@admin.register(models.BalanceHistory)
class BalanceHistoryAdmin(admin.ModelAdmin):
    list_display = ('client', 'source', 'amount')
    list_filter = ('source',)
    search_fields = ('client__name',)


@admin.register(models.StatisticByAgencyClient)
class StatisticByAgencyClientAdmin(admin.ModelAdmin):
    list_display = ('date', 'source', 'client')
    list_filter = ('source',)
    search_fields = ('client__name',)
    ordering = ['client__pk']

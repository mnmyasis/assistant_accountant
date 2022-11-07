from django.contrib import admin

from . import models

admin.site.register(models.Source)
admin.site.register(models.Token)
admin.site.register(models.VkAccount)
admin.site.register(models.Campaign)
admin.site.register(models.AgencyClient)
admin.site.register(models.BalanceHistory)
admin.site.register(models.StatisticByAgencyClient)
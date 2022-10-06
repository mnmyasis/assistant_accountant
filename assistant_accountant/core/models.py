from django.db import models


class UpdateModel(models.Model):
    updated = models.DateTimeField(
        'Дата изменения',
        auto_now=True
    )

    class Meta:
        abstract = True


class CreateModel(models.Model):
    created = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )

    class Meta:
        abstract = True

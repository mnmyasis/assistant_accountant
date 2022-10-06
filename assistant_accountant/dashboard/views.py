from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.conf import settings
from django.urls import reverse

from core.yandex import direct
from . import models


@login_required
def index(request):
    context = {
        'yandex_direct_verification_code_url':
            direct.get_url_verification_code_request(
                client_id=settings.YANDEX_DIRECT_CLIENT_ID
            )
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def yandex_direct_callback(request):
    data = direct.exchange_code_on_token(
        client_id=settings.YANDEX_DIRECT_CLIENT_ID,
        client_secret=settings.YANDEX_DIRECT_CLIENT_SECRET,
        code=request.GET['code']
    )
    if data.get('access_token') is None or data.get('refresh_token') is None:
        raise ValueError(
            'Access or refresh_token is NULL.'
        )
    if isinstance(int, data.get('expires_in')) is False:
        raise TypeError(
            'Expires_in not int.'
        )

    models.YandexDirectToken.objects.update_or_create(
        user=request.user,
        defaults={
            'user': request.user,
            'access_token': data.get('access_token'),
            'refresh_token': data.get('refresh_token'),
            'expires_in': data.get('expires_in'),
        }
    )
    return redirect(
        reverse('dashboard:index')
    )
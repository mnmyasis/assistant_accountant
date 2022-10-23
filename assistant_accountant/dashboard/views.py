from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
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
    expires_in = data.get('expires_in')
    if isinstance(expires_in, int) is False:
        raise TypeError(
            f'Expires_in not int. {expires_in} {type(expires_in)}'
        )

    models.YandexDirectToken.objects.update_or_create(
        user=request.user,
        defaults={
            'user': request.user,
            'access_token': data.get('access_token'),
            'refresh_token': data.get('refresh_token'),
            'expires_in': expires_in,
        }
    )
    return redirect(
        reverse('dashboard:index')
    )


@login_required
def yandex_test(request):
    token = get_object_or_404(models.YandexDirectToken, user=request.user)
    selection_criteria = {
        'Archived': 'NO'
    }
    field_names = ['Login', 'ClientId']
    data = direct.AgencyClients(access_token=token.access_token,
                                selection_criteria=selection_criteria,
                                field_names=field_names,
                                on_sandbox=True).get()
    print(data)
    clients = data[0]['result']['Clients']
    for client in clients:
        data = direct.ClientCostReport(access_token=token.access_token,
                                       client_login=client['Login'],
                                       on_sandbox=True).get()
        print(data)
    return redirect(
        reverse('about:index')
    )
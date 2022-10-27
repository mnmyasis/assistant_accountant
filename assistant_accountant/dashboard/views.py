import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.urls import reverse

from core.yandex import direct
from core.vk.auth import get_auth_url, get_access_token
from core.vk import ads
from core.my_target import auth, exceptions
from core.my_target import ads as my_target_ads
from . import models


@login_required
def index(request):
    context = {
        'yandex_direct_verification_code_url':
            direct.get_url_verification_code_request(
                client_id=settings.YANDEX_DIRECT_CLIENT_ID
            ),
        'vk_ads_auth_url': get_auth_url(
            client_id=settings.VK_CLIENT_ID,
            redirect_uri=settings.VK_REDIRECT_URL
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


def vk_callback(request):
    access_token, expires_in = get_access_token(
        client_id=settings.VK_CLIENT_ID,
        client_secret=settings.VK_CLIENT_SECRET,
        redirect_uri=settings.VK_REDIRECT_URL,
        code=request.GET.get('code')
    )
    models.VkAdsToken.objects.update_or_create(
        user=request.user,
        defaults={
            'user': request.user,
            'access_token': access_token,
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


@login_required
def vk_test(request):
    vk_tokens = models.VkAdsToken.objects.get(user=request.user)
    data = ads.Account(access_token=vk_tokens.access_token).get()
    # print(data)
    result = []
    accounts = data['response'][0]['account_id'], data['response'][1][
        'account_id']
    for account in accounts:
        data = ads.Clients(access_token=vk_tokens.access_token,
                           account_id=account).get()
        res = {
            'account_id': account
        }
        ids = []

        for line in data['response']:
            ids.append(line['id'])
        res['client_ids'] = ids
        result.append(res)

        data = ads.Statistic(
            access_token=vk_tokens.access_token,
            account_id=account,
            ids=ids,
            date_from='2014',
            date_to='2022'
        ).get()
        print(data)
    # print(result)
    return redirect(
        reverse('about:index')
    )


@login_required
def my_target_auth(request):
    try:
        response = auth.ClientCredentialsToken(
            client_id=settings.MY_TARGET_CLIENT_ID,
            client_secret=settings.MY_TARGET_CLIENT_SECRET
        ).run()
    except exceptions.MyTargetTokenLimitError as error:
        user_id = error.args[0].get('user_id')
        auth.DeleteTokens(
            client_id=settings.MY_TARGET_CLIENT_ID,
            client_secret=settings.MY_TARGET_CLIENT_SECRET,
            user_id=user_id
        ).run()
        response = auth.ClientCredentialsToken(
            client_id=settings.MY_TARGET_CLIENT_ID,
            client_secret=settings.MY_TARGET_CLIENT_SECRET
        ).run()
    print(response)
    access_token = response.get('access_token')
    refresh_token = response.get('refresh_token')
    expires_in = response.get('expires_in')
    token, _ = models.MyTargetToken.objects.update_or_create(
        user=request.user,
        defaults={
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': expires_in
        }
    )
    return redirect(
        reverse('about:index')
    )


@login_required
def my_target_test(request):
    my_target = models.MyTargetToken.objects.get(user=request.user)
    data = my_target_ads.AgencyClients(my_target.access_token).run()
    print(data)
    ids = []
    for line in data:
        ids.append(line['user']['id'])
    data = my_target_ads.SummaryStatistic(
        my_target.access_token,
        ids=ids,
        date_from='2022-01-01',
        date_to='2022-10-25'
    ).run()
    print(data)
    return redirect(
        reverse('about:index')
    )

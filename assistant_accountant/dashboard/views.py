import json

from django.contrib.auth.decorators import login_required
from django.db.models import Max, Count, Q, F
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.urls import reverse

from core.yandex import direct
from core.vk.auth import get_auth_url, get_access_token
from core.vk import ads
from core.my_target import auth, exceptions
from core.my_target import ads as my_target_ads
from . import models
from . import google_sheets


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
    source = models.Source.objects.get(name=models.YANDEX_DIRECT)
    models.Token.objects.update_or_create(
        user=request.user,
        source=source,
        defaults={
            'user': request.user,
            'access_token': data.get('access_token'),
            'refresh_token': data.get('refresh_token'),
            'expires_in': expires_in,
            'source': source
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
    source = models.Source.objects.get(name=models.VK_ADS)
    models.Token.objects.update_or_create(
        user=request.user,
        source=source,
        defaults={
            'user': request.user,
            'access_token': access_token,
            'expires_in': expires_in,
            'source': source

        }
    )
    return redirect(
        reverse('dashboard:index')
    )


@login_required
def yandex_test(request):
    token = get_object_or_404(models.Token, user=request.user,
                              source__name=models.YANDEX_DIRECT)
    selection_criteria = {
        'Archived': 'NO'
    }
    field_names = ['Login', 'ClientId', 'OverdraftSumAvailable', 'ClientInfo',
                   'AccountQuality']
    payload = direct.Payload.payload_pagination(
        criteria=selection_criteria,
        fields=field_names,
        limit=2000,
        offset=0,
        method='get'
    )
    on_sandbox = False
    data = direct.AgencyClients(access_token=token.access_token,
                                payload=payload,
                                on_sandbox=on_sandbox).get()
    # for line in data:
    #     print(json.dumps(line, indent=4))
    i = 0
    logins = []
    for client in data:
        print(data)
        print(client['Login'], ' ', client['ClientId'])
        logins.append(client['Login'])
        # payload = direct.Payload.payload_statistic(
        #     fields=['Date', 'Cost'],
        #     criteria={'DateFrom': '2022-11-01', 'DateTo': '2022-11-02'},
        #     params=[
        #         ('ReportName', 'ACCOUNT_COST'),
        #         ('ReportType', 'ACCOUNT_PERFORMANCE_REPORT'),
        #         ('DateRangeType', 'CUSTOM_DATE'),
        #         ('Format', 'TSV'),
        #         ('IncludeVAT', 'NO'),
        #         ('IncludeDiscount', 'NO')
        #     ],
        # )
        #
        # data_ = direct.ClientCostReport(access_token=token.access_token,
        #                                 client_login=client['Login'],
        #                                 payload=payload,
        #                                 on_sandbox=False).get()

        # payload = direct.Payload.payload_pagination(
        #     limit=10000,
        #     offset=0,
        #     method='get',
        #     fields=['Id', 'Name', 'Type', 'Funds']
        # )
        # data_ = direct.Campaigns(
        #     access_token=token.access_token,
        #     payload=payload,
        #     client_login=client['Login'],
        #     on_sandbox=on_sandbox
        # ).get()
        # print(json.dumps(data_, indent=4))

    payloads = direct.PayloadV4.payload_account_management(
        logins=logins
    )
    for payload in payloads:
        data = direct.AccountManagement(
            access_token=token.access_token,
            payload=payload,
            on_sandbox=on_sandbox
        ).get()
        print(json.dumps(data, indent=4))
    return redirect(
        reverse('about:index')
    )


@login_required
def vk_test(request):
    vk_tokens = models.Token.objects.get(user=request.user,
                                         source__name=models.VK_ADS)
    data = ads.Account(access_token=vk_tokens.access_token).get()
    print(data)
    result = []
    accounts = data['response'][0]['account_id'], data['response'][1][
        'account_id']
    for account in accounts:
        data = ads.Clients(access_token=vk_tokens.access_token,
                           account_id=account).get()
        print(account)
        res = {
            'account_id': account
        }
        ids = []
        # data = ads.GetBudget(access_token=vk_tokens.access_token,
        #                      account_id=str(account)).get()
        for line in data['response']:
            ids.append(line['id'])
        res['client_ids'] = ids
        result.append(res)

        data = ads.Statistic(
            access_token=vk_tokens.access_token,
            account_id=account,
            id_clients=ids,
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
    source = models.Source.objects.get(name=models.MY_TARGET)
    token, _ = models.Token.objects.update_or_create(
        user=request.user,
        source=source,
        defaults={
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': expires_in,
            'source': source
        }
    )
    return redirect(
        reverse('about:index')
    )


@login_required
def my_target_test(request):
    my_target = models.Token.objects.get(user=request.user,
                                         source__name=models.MY_TARGET)
    data = my_target_ads.AgencyClients(my_target.access_token).run()
    ids = []
    for line in data:
        # print(json.dumps(line, indent=4))
        ids.append(line['user']['id'])
    ids = [ids[0], ]
    data = my_target_ads.SummaryStatistic(
        my_target.access_token,
        clients_id=ids,
        date_from='2022-10-20',
        date_to='2022-10-25'
    ).run()
    print(json.dumps(data, indent=4))
    return redirect(
        reverse('about:index')
    )


def sheets_view(request):
    credentials = google_sheets.get_credentials(
        private_key=settings.GOOGLE_SHEETS_PRIVATE_KEY,
        private_key_id=settings.GOOGLE_SHEETS_PRIVATE_KEY_ID,
        client_email=settings.GOOGLE_SHEETS_CLIENT_EMAIL,
        client_id=settings.GOOGLE_SHEETS_CLIENT_ID
    )
    ws = google_sheets.WorkSheet.get(
        'ditexos',
        'h1',
        credentials
    )
    gs_redactor = google_sheets.Redactor.google_sheets_redactor_by_tag(
        ws,
        '#DITEXOS',
        alphabet=google_sheets.AlphabetGoogleSheets()
    )
    columns = [
        [1, 1, 's', 1, 1],
        [2, 2, 10, 2, 2]
    ]
    gs_redactor.update(columns)
    print(ws)


def test(request):
    month = '11'
    client = request.user.agency_clients.select_related(
        'source'
    ).all().prefetch_related(
        'statistic_by_agency_clients'
    ).prefetch_related(
        'balance_history'
    ).filter(
        balance_history__date__month=month,
        statistic_by_agency_clients__date__month=month
    ).annotate(
        amount_max=Max('balance_history__amount'),
        cost_max=Max('statistic_by_agency_clients__cost')
    ).filter(Q(cost_max__gt=0) | Q(amount_max__gt=0)).values(
        'statistic_by_agency_clients__date__month',
        'name',
        'cost_max',
        'amount_max',
        month=F('balance_history__date__month'),
        source_name=F('source__name'),
    ).order_by('name')
    return render(request, 'dashboard/index.html', {'res': {}, 'data': client})

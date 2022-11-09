from abc import ABC, abstractmethod
from time import sleep
from typing import List, Dict, Any

from django.conf import settings

from .models import YANDEX_DIRECT, MY_TARGET, VK_ADS, Token
from core.yandex.direct import AgencyClients, Payload, ClientCostReport
from core.vk import ads as vk_ads
from core.vk.exceptions import (VkFloodControlError,
                                VkManyRequestPerSecondError,
                                VKMaxCountAttemptError)
from core.my_target import ads as my_target_ads
from core.my_target import auth as my_target_auth
from core.my_target.exceptions import (MyTargetExpiredTokenError,
                                       MyTargetMaxAttemptCountError)


class Ads(ABC):

    @abstractmethod
    def get(self):
        ...


class API:

    def __init__(self, ads: Ads):
        self.ads = ads

    def collect_data_ads(self):
        return self.ads.get()


class Yandex(Ads):

    def __init__(self, user_id: int, on_sandbox=False):
        self.on_sandbox = on_sandbox
        self.user_id = user_id
        self.tokens = Token.objects.get(user__pk=self.user_id,
                                        source__name=YANDEX_DIRECT)


class YandexAgencyClients(Yandex):
    LIMIT = 2000
    METHOD = 'get'

    def get_selection_criteria(self) -> Dict:
        return {'Archived': 'NO'}

    def get_fields(self) -> List[str]:
        return ['Login', 'ClientId', 'ClientInfo']

    def get_payload(self) -> Payload:
        return Payload.payload_pagination(
            criteria=self.get_selection_criteria(),
            fields=self.get_fields(),
            limit=self.LIMIT,
            offset=0,
            method=self.METHOD
        )

    def prepare_data(self, data):
        agency_clients = []
        for raw in data:
            cl = {
                'client_id': raw['ClientId'],
                'name': raw['Login'],
                'source': YANDEX_DIRECT,
                'user_id': self.user_id
            }
            agency_clients.append(cl)
        return agency_clients

    def get(self):
        data = AgencyClients(access_token=self.tokens.access_token,
                             payload=self.get_payload(),
                             on_sandbox=self.on_sandbox).get()
        data = self.prepare_data(data)
        return data


class YandexStatistic(Yandex):

    def __init__(
            self,
            user_id: int,
            client_login: str,
            date_from: str,
            date_to: str,
            on_sandbox: bool = False):
        self.client_login = client_login
        self.date_from = date_from
        self.date_to = date_to
        super().__init__(user_id=user_id, on_sandbox=on_sandbox)

    def get_payload(self) -> Payload:
        payload = Payload.payload_statistic(
            fields=['Cost', 'Clicks'],
            criteria={'DateFrom': self.date_from, 'DateTo': self.date_to},
            params=[
                ('ReportName', 'ACCOUNT_COST'),
                ('ReportType', 'ACCOUNT_PERFORMANCE_REPORT'),
                ('DateRangeType', 'CUSTOM_DATE'),
                ('Format', 'TSV'),
                ('IncludeVAT', 'NO'),
                ('IncludeDiscount', 'NO')
            ],
        )
        return payload

    def prepare_data(self, data):
        return data

    def get(self):
        data = ClientCostReport(access_token=self.tokens.access_token,
                                client_login=self.client_login,
                                payload=self.get_payload(),
                                on_sandbox=self.on_sandbox).get()
        data = self.prepare_data(data)
        return data


class VKCollectData(Ads):
    FLOOD_TIMEOUT = 60
    REQUEST_PER_SECOND_TIMEOUT = 20
    MAX_COUNT_ATTEMPT = 10

    def __init__(self, user_id: int, date_from: str, date_to: str):
        self.user_id = user_id
        self.date_from = date_from
        self.date_to = date_to
        self.tokens = Token.objects.get(user=self.user_id,
                                        source__name=VK_ADS)
        self.data = {}

    def prepare_agency_clients(self, account_id, data):
        for raw in data['response']:
            client_id = raw['id']
            if self.data.get(client_id):
                raise ValueError(
                    'client_id already exists: {}'.format(client_id))
            self.data[client_id] = {
                'stats': [],
                'name': raw['name'],
                'client_id': client_id,
                'user_id': self.user_id,
                'account_id': account_id,
                'source': VK_ADS,
            }

    def prepare_statistic(self, data):
        for raw in data['response']:
            for stat in raw['stats']:
                client_id = raw['id']
                self.data[client_id]['stats'].append(
                    {
                        'date': stat['day'],
                        'cost': stat.get('spent', 0.0),
                    }
                )

    def get_clients_id(self, ag_data) -> List[int]:
        id_clients = [raw['id'] for raw in ag_data['response']]
        return id_clients

    def get_accounts_id(self) -> List[int]:
        accounts = vk_ads.Account(
            access_token=self.tokens.access_token).get()
        accounts_id = []
        for account in accounts['response']:
            accounts_id.append(account['account_id'])
        return accounts_id

    def api_request(self, vk_api: vk_ads.BaseApi):
        attempt_count = 0
        while True:
            if attempt_count == self.MAX_COUNT_ATTEMPT:
                raise VKMaxCountAttemptError()
            attempt_count += 1
            try:
                data = vk_api.get()
                return data
            except VkFloodControlError:
                print('flood error')
                sleep(self.FLOOD_TIMEOUT)
            except VkManyRequestPerSecondError:
                print('per second error')
                sleep(self.REQUEST_PER_SECOND_TIMEOUT)

    def get_data(self) -> List:
        return list(self.data.values())

    def get(self, count_attempt=0) -> List[Dict[Any, Any]]:
        for account_id in self.get_accounts_id():
            agency_clients = vk_ads.Clients(
                access_token=self.tokens.access_token,
                account_id=account_id
            )
            ag_data = self.api_request(agency_clients)
            self.prepare_agency_clients(account_id, ag_data)
            statistic = vk_ads.Statistic(
                access_token=self.tokens.access_token,
                account_id=account_id,
                id_clients=self.get_clients_id(ag_data),
                date_from='2022-11-01',
                date_to='2022-11-09',
                period='day'
            )
            stat_data = self.api_request(statistic)
            self.prepare_statistic(stat_data)
        return self.get_data()


class MyTargetCollectData(Ads):
    MAX_ATTEMPT_COUNT = 10

    def __init__(self, user_id, date_from: str, date_to: str):
        self.user_id = user_id
        self.date_from = date_from
        self.date_to = date_to
        self.tokens = Token.objects.get(user=self.user_id,
                                        source__name=MY_TARGET)
        self.data = {}

    def refresh_token(self):
        tokens = my_target_auth.RefreshToken(
            client_id=settings.MY_TARGET_CLIENT_ID,
            client_secret=settings.MY_TARGET_CLIENT_SECRET,
            refresh_token=self.tokens.refresh_token
        ).run()
        self.tokens.access_token = tokens['access_token']
        self.tokens.refresh_token = tokens['refresh_token']
        self.tokens.expires_in = tokens['expires_in']
        self.tokens.save()

    def prepare_agency_clients(self, ag_data):
        for raw in ag_data:
            client_id = raw['user']['id']
            self.data[client_id] = {
                'stats': [],
                'name': raw['user']['client_username'],
                'source': MY_TARGET,
                'user_id': self.user_id,
                'client_id': client_id
            }

    def prepare_statistic(self, stat_data):
        for item in stat_data['items']:
            client_id = item['id']
            for row in item['rows']:
                self.data[client_id]['stats'].append({
                    'date': row['date'],
                    'cost': float(row['base']['spent'])
                })

    def api_request(self, my_target_api: my_target_ads.BaseApi):
        attempt_count = 0
        while True:
            if attempt_count == self.MAX_ATTEMPT_COUNT:
                raise MyTargetMaxAttemptCountError('Max attempt count.')
            attempt_count += 1
            try:
                data = my_target_api.run()
                return data
            except MyTargetExpiredTokenError:
                self.refresh_token()

    def get_data(self) -> List:
        return list(self.data.values())

    def get_clients_id(self, ag_data: List) -> List[int]:
        return [raw['user']['id'] for raw in ag_data]

    def get(self):
        agency_clients = my_target_ads.AgencyClients(
            self.tokens.access_token)
        ag_data = self.api_request(agency_clients)
        self.prepare_agency_clients(ag_data)
        statistic = my_target_ads.DayStatistic(
            self.tokens.access_token,
            clients_id=self.get_clients_id(ag_data),
            date_from=self.date_from,
            date_to=self.date_to
        )
        stat_data = self.api_request(statistic)
        self.prepare_statistic(stat_data)
        return self.get_data()

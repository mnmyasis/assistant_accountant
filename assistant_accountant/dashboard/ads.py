from abc import ABC, abstractmethod
from time import sleep
from typing import List, Dict

from django.conf import settings

from .models import YANDEX_DIRECT, MY_TARGET, VK_ADS, Token
from core.yandex.direct import AgencyClients, Payload
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

    def agency_clients(self):
        return self.ads.get()


class YandexAgencyClients(Ads):
    LIMIT = 2000
    METHOD = 'get'

    def __init__(self, user_id: int, on_sandbox=False):
        self.on_sandbox = on_sandbox
        self.user_id = user_id
        self.tokens = Token.objects.get(user__pk=self.user_id,
                                        source__name=YANDEX_DIRECT)

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


class VKAgencyClients(Ads):
    FLOOD_TIMEOUT = 60
    REQUEST_PER_SECOND_TIMEOUT = 20
    MAX_COUNT_ATTEMPT = 10

    def __init__(self, user_id):
        self.user_id = user_id
        self.tokens = Token.objects.get(user=self.user_id, source__name=VK_ADS)

    def get_accounts_id(self) -> List[int]:
        accounts = vk_ads.Account(access_token=self.tokens.access_token).get()
        accounts_id = []
        for account in accounts['response']:
            accounts_id.append(account['account_id'])
        return accounts_id

    def prepare_data(self, data) -> List[Dict]:
        account_id = data['account_id']
        agency_clients = []
        for raw in data['agency_clients']['response']:
            cl = {
                'client_id': raw['id'],
                'name': raw['name'],
                'account_id': account_id,
                'source': VK_ADS,
                'user_id': self.user_id
            }
            agency_clients.append(cl)

        return agency_clients

    def _run(self):
        data = []
        for account_id in self.get_accounts_id():
            agency_clients = vk_ads.Clients(
                access_token=self.tokens.access_token,
                account_id=account_id).get()

            data += self.prepare_data({
                'account_id': account_id,
                'agency_clients': agency_clients
            })
        return data

    def get(self, count_attempt=0) -> List[Dict]:
        if count_attempt == self.MAX_COUNT_ATTEMPT:
            raise VKMaxCountAttemptError('Max count attempt response.')
        count_attempt += 1
        try:
            data = self._run()
            return data
        except VkFloodControlError:
            sleep(self.FLOOD_TIMEOUT)
            return self.get(count_attempt)
        except VkManyRequestPerSecondError:
            sleep(self.REQUEST_PER_SECOND_TIMEOUT)
            return self.get(count_attempt)


class MyTargetAgencyClients(Ads):
    MAX_ATTEMPT_COUNT = 10

    def __init__(self, user_id):
        self.user_id = user_id
        self.tokens = Token.objects.get(user=self.user_id,
                                        source__name=MY_TARGET)

    def prepare_data(self, data):
        agency_clients = []
        for raw in data:
            cl = {
                'client_id': raw['user']['id'],
                'name': raw['user']['client_username'],
                'source': MY_TARGET,
                'user_id': self.user_id
            }
            agency_clients.append(cl)
        return agency_clients

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

    def get(self, attempt_count=0):
        if attempt_count == self.MAX_ATTEMPT_COUNT:
            raise MyTargetMaxAttemptCountError('Max attempt count.')
        attempt_count += 1
        try:
            data = my_target_ads.AgencyClients(self.tokens.access_token).run()
            data = self.prepare_data(data)
            return data
        except MyTargetExpiredTokenError:
            self.refresh_token()
            return self.get(attempt_count=attempt_count)

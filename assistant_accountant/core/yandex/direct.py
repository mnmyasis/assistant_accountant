import json
from typing import List, Dict

import requests
from http import HTTPStatus

from requests import Response

from . import exceptions

URL = 'https://api.direct.yandex.com/'
SANDBOX_URL = 'https://api-sandbox.direct.yandex.com/'

VERSION_API = 'json/v5/'

REPORT_TYPE = 'ACCOUNT_PERFORMANCE_REPORT'


def get_url(on_sandbox=False):
    if on_sandbox:
        return SANDBOX_URL + VERSION_API
    return URL + VERSION_API


def get_url_verification_code_request(client_id):
    """Формируется урл для получения кода подтвержедения."""
    url = 'https://oauth.yandex.ru/authorize'
    payload = {
        'response_type': 'code',
        'client_id': client_id
    }
    return requests.get(url, payload).url


def exchange_code_on_token(client_id, client_secret, code):
    """Обмен кода подтверждения на токен."""
    url = 'https://oauth.yandex.ru/token'
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret
    }
    try:
        response = requests.post(url, data=data)
    except Exception as error:
        raise exceptions.ExchangeCodeOnTokenError(error)

    if response.status_code != HTTPStatus.OK:
        raise exceptions.ExchangeCodeOnTokenError(
            f'Код ответа API: {response.status_code}, '
            f'параметры запроса: {data}, '
            f'endpoint: {url}'
        )
    response_json = response.json()
    if response_json.get('error'):
        raise exceptions.ExchangeCodeOnTokenError(
            'error_description: {}, error: {}'.format(
                response_json.get('error_description'),
                response_json.get('error')
            )
        )
    return response_json


def clients(access_token):
    headers = {
        "Authorization": "Bearer " + access_token,
        "Accept-Language": "ru"
    }
    limit = 10000
    offset = 0
    data = []
    service = 'agencyclients'
    while True:
        agency_client_body = {
            "method": "get",
            "params": {
                "SelectionCriteria": {
                    "Archived": "NO"
                },
                "FieldNames": ["Login", "ClientId"],
                "ContractFieldNames": ["Price", ],
                "Page": {
                    "Limit": limit,
                    "Offset": offset
                }
            }
        }
        url = get_url(on_sandbox=True) + service
        response = requests.post(
            url,
            json.dumps(agency_client_body),
            headers=headers
        )

        print(response.status_code)
        response_json = response.json()
        if response_json.get('error'):
            error = response_json['error']
            raise exceptions.YandexDirectApiRequestError(
                f'Код ответа API: {response.status_code}, '
                f'RequestId: {response.headers.get("RequestId")}, '
                f'Ответ: {error}, '
                f'endpoint: {url}'
            )
        if not response_json['result']:
            print(data)
            return data

        data.append(response_json)
        if response_json['result'].get("LimitedBy"):
            agency_client_body['Page']['Offset'] = response_json['result'][
                "LimitedBy"]
        else:
            return data


class BaseApi:
    """
    Базовый класс для работы с API Яндекс Директ.\n
    BaseApi(access_token=...,
            selection_criteria=...,\n
            field_names=...,\n
            on_sandbox=False,\n
            language='ru').get()
    """

    URL = 'https://api.direct.yandex.com/'
    SANDBOX_URL = 'https://api-sandbox.direct.yandex.com/'
    VERSION_API = 'json/v5/'
    PARAMS_KEY = 'params'

    def __init__(
            self,
            access_token: str,
            selection_criteria: Dict,
            field_names: List[str],
            on_sandbox=False,
            language='ru'
    ):
        self.access_token = access_token
        self.selection_criteria = selection_criteria
        self.field_names = field_names
        self.on_sandbox = on_sandbox
        self.language = language

    @property
    def endpoint_service(self) -> str:
        """Endpoint сервиса API."""
        raise NotImplementedError

    @property
    def headers(self) -> Dict[str, str]:
        """HTTP заголовки."""
        return {
            "Authorization": "Bearer " + self.access_token,
            "Accept-Language": self.language
        }

    def get_headers(self) -> Dict[str, str]:
        """
        Возвращает заголовки запроса. Переопределить в дочернем классе,
        если необходимы дополнительные параметры.
        :returns: headers
        """
        return self.headers

    def get_url(self) -> str:
        """Возвращает урл для запроса."""
        url = '{base_url}{version}{service}'
        if self.on_sandbox:
            url.format(base_url=self.SANDBOX_URL)
        else:
            url.format(base_url=self.URL)

        return url.format(
            version=self.VERSION_API,
            service=self.endpoint_service
        )

    @property
    def __payload(self):
        """Парметры запроса."""
        return {
            self.PARAMS_KEY: {
                "SelectionCriteria": self.selection_criteria,
                "FieldNames": self.field_names,
            }
        }

    def set_params_payload(self, key, value):
        """Установка дополнительных параметров."""
        if not key or not value:
            raise ValueError()
        if self.__payload[self.PARAMS_KEY].get(key):
            raise exceptions.ParamsAlreadyExistError(
                f'{key} already exists in params'
            )
        self.__payload[self.PARAMS_KEY][key] = value

    def get_payload(self) -> Dict:
        """
        Возвращает payload.\n
        Если потребуется расширить параметры запроса,
        необходимо переопределить данную функцию и передать необходимые
        параметры через set_params_payload.\n
        def get_payload(self) -> Dict:
            self.set_params_payload(key=..., value...)\n
            return super().get_payload()
        :return: payload
        """
        return self.__payload

    def api_request(
            self,
            url: str,
            headers: Dict[str, str],
            payload: Dict
    ) -> Dict:
        """Запрос к API."""
        status_code = None
        try:
            response = requests.post(
                url,
                json.dumps(payload),
                headers=headers
            )
            status_code = response.status_code
            response.raise_for_status()
        except Exception as error:
            raise exceptions.YandexDirectApiRequestError(
                f'Api request error url: {url} '
                f'payload: {payload} '
                f'headers:  {headers}'
                f'status_code: {status_code} '
                f'error: {error}'
            )
        return response.json()

    def check_response(self, response: Dict) -> Dict:
        """Проверка ответа от API директа."""
        if not isinstance(response, dict):
            raise TypeError(
                f'The response it shuold be dict, not a {type(response)}'
            )
        if response.get('error'):
            error = response['error']
            raise exceptions.YandexDirectResponseError(
                f'Endpoint: {self.endpoint_service}'
                f'Payload: {self.__payload}'
                f'Error: {error}'
            )
        return response

    def get(self) -> Dict:
        """
        Пользовательский интерфейс и оркестратор.
        :return: response
        """
        payload = self.get_payload()
        url = self.get_url()
        headers = self.get_headers()
        response = self.api_request(url=url, headers=headers, payload=payload)
        response = self.check_response(response)
        return response


if __name__ == '__main__':
    print(get_url())

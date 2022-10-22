import json
from typing import List, Dict

import requests
from http import HTTPStatus

from . import exceptions


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
        self.status_code = None

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
        if self.on_sandbox:
            url = self.SANDBOX_URL
        else:
            url = self.URL

        return url + self.VERSION_API + self.endpoint_service

    @property
    def __payload(self):
        """Парметры запроса."""
        return {
            'method': 'get',
            self.PARAMS_KEY: {
                "SelectionCriteria": self.selection_criteria,
                "FieldNames": self.field_names,
            }
        }

    def set_params_payload(self, key, value):
        """Установка дополнительных параметров."""
        if not key or not value:
            raise ValueError()
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
        try:
            response = requests.post(
                url,
                json.dumps(payload),
                headers=headers
            )
            self.status_code = response.status_code
            response.raise_for_status()
        except Exception as error:
            raise exceptions.YandexDirectApiRequestError(
                f'Api request error url: {url} '
                f'payload: {payload} '
                f'headers:  {headers} '
                f'status_code: {self.status_code} '
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
                f'Endpoint: {self.endpoint_service} '
                f'Payload: {self.__payload} '
                f'Error: {error} '
                f'Full url: {self.get_url()}'
            )
        return response

    def run_api_request(self) -> Dict:
        """Оркестратор."""
        payload = self.get_payload()
        url = self.get_url()
        headers = self.get_headers()
        response = self.api_request(url=url, headers=headers, payload=payload)
        response = self.check_response(response)
        return response

    def get(self):
        """
        Пользовательский интерфейс.
        Переопределить в дочернем классе, если потребуется
        дополнительная логика.
        :return: response
        """
        response = self.run_api_request()
        return response


class AgencyClients(BaseApi):
    """
    Получает список клиентов агентства из API Яндекс директ.\n
    AgencyClients(access_token=...,
                selection_criteria=...,\n
                field_names=...,\n
                on_sandbox=False,\n
                language='ru').get()
    """
    ENDPOINT = 'agencyclients'
    LIMIT = 10000
    OFFSET = 0
    CONTRACT_FIELD_NAMES = {'ContractFieldNames': ["Price", ]}
    PAGINATION_PARAMS = {
        'Page': {
            'Limit': LIMIT,
            'Offset': OFFSET
        }
    }
    RESULT_KEY = 'result'
    LIMITED_BY_KEY = 'LimitedBy'

    @property
    def endpoint_service(self) -> str:
        """Endpoint сервиса."""
        return self.ENDPOINT

    def get_payload(self) -> Dict:
        """Устанавливает дополнительные параметры в payload."""
        for params in [self.CONTRACT_FIELD_NAMES, self.PAGINATION_PARAMS]:
            for key, value in params.items():
                self.set_params_payload(key, value)
        return super().get_payload()

    def change_offset(self, limited_by):
        """Меняет параметр offset в payload."""
        self.OFFSET = limited_by
        for key, value in self.PAGINATION_PARAMS.items():
            self.set_params_payload(key, value)

    def get(self):
        data = []
        has_all_clients_received = False
        while not has_all_clients_received:
            response = self.run_api_request()
            limited_by = response[self.RESULT_KEY].get(self.LIMITED_BY_KEY)
            data.append(response)
            if limited_by:
                self.change_offset(limited_by)
            else:
                has_all_clients_received = True
        return data


if __name__ == '__main__':
    ...

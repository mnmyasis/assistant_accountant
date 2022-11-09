import json
from enum import Enum
from time import sleep
from typing import List, Dict, Tuple

import requests
from http import HTTPStatus
from requests import Response

from . import exceptions


class Endpoints(Enum):
    AGENCY_CLIENTS = 'agencyclients'
    REPORTS = 'reports'
    CAMPAIGNS = 'campaigns'
    TOKEN = 'token'
    AUTHORIZE = 'authorize'


def get_url_verification_code_request(client_id):
    """Формируется урл для получения кода подтвержедения."""
    url = 'https://oauth.yandex.ru/' + Endpoints.AUTHORIZE.value
    payload = {
        'response_type': 'code',
        'client_id': client_id
    }
    return requests.get(url, payload).url


def exchange_code_on_token(client_id, client_secret, code):
    """Обмен кода подтверждения на токен."""
    url = 'https://oauth.yandex.ru/' + Endpoints.TOKEN.value
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


class Payload:

    def __init__(self):
        self.name = 'params'
        self.payload = {
            self.name: {
                'FieldNames': []
            },
        }

    def add_criteria(self, criteria: dict):
        current = self.payload[self.name].get('SelectionCriteria')
        if current:
            current.update(criteria)
        else:
            self.payload[self.name]['SelectionCriteria'] = criteria

    def add_field(self, field: str):
        self.payload[self.name]['FieldNames'].append(field)
        return self

    def get_fields(self):
        return self.payload[self.name].get('FieldNames')

    def add_page(self, offset: int, limit: int):
        self.payload[self.name].update(
            {'Page': {'Limit': limit, 'Offset': offset}}
        )

    def add_params(self, key: str, value: str):
        self.payload[self.name][key] = value

    def change_offset(self, offset):
        self.payload[self.name]['Page']['Offset'] = offset

    def add_method(self, method: str):
        self.payload['method'] = method

    def __str__(self):
        return str(json.dumps(self.payload, indent=4))

    @staticmethod
    def payload_fields(fields, criteria: Dict = None, method=None):
        payload = Payload()
        if method:
            payload.add_method(method)
        for field in fields:
            payload.add_field(field)
        if criteria:
            payload.add_criteria(criteria)
        return payload

    @staticmethod
    def payload_pagination(fields, offset, limit, criteria: Dict = None,
                           method=None):
        payload = Payload()
        if method:
            payload.add_method(method)
        for field in fields:
            payload.add_field(field)
        if criteria:
            payload.add_criteria(criteria)
        payload.add_page(offset=offset, limit=limit)
        return payload

    @staticmethod
    def payload_statistic(fields, params: List[Tuple], criteria: Dict = None):
        payload = Payload()
        for field in fields:
            payload.add_field(field)
        if criteria is None:
            criteria = {}
        payload.add_criteria(criteria)
        for param in params:
            payload.add_params(*param)
        return payload


class BaseApi:
    """
    Базовый класс для работы с API Яндекс Директ.\n
    BaseApi(access_token=...,
            payload=...,\n
            on_sandbox=False,\n
            language='ru').get()
    """

    URL = 'https://api.direct.yandex.com/'
    SANDBOX_URL = 'https://api-sandbox.direct.yandex.com/'
    VERSION_API = 'json/v5/'

    def __init__(
            self,
            access_token: str,
            payload: Payload,
            on_sandbox=False,
            language='ru'
    ):

        self.access_token = access_token
        self.payload = payload
        self.on_sandbox = on_sandbox
        self.language = language
        self.status_code = None

    @property
    def endpoint_service(self) -> Endpoints:
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

        return f'{url}{self.VERSION_API}{self.endpoint_service.value}'

    def get_payload(self) -> Payload:
        """
        Возвращает payload.
        :return:payload
        """
        return self.payload

    def get_response(self, url, payload, headers) -> Response:
        """
        Делает запрос и возвращает ответ.
        Переопределить в дочернем классе, если требуется расширение логики
        запроса.
        :param url:
        :param payload:
        :param headers:
        :return: response
        """
        return requests.post(
            url,
            str(payload),
            headers=headers
        )

    def api_response_decode(self, response):
        """
        Декодирование ответа от апи. Сделан для возможности расширения логики в
        дочерних классах.
        """
        return response.json()

    def api_request(
            self,
            url: str,
            headers: Dict[str, str],
            payload: Payload
    ) -> Response:
        """Запрос к API."""
        try:
            response = self.get_response(
                url,
                payload,
                headers
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
        return response

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
                f'Payload: {self.get_payload()} '
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
        response = self.api_response_decode(response)
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
                payload=...,\n
                on_sandbox=False,\n
                language='ru').get()
    """
    RESULT_KEY = 'result'
    LIMITED_BY_KEY = 'LimitedBy'

    @property
    def endpoint_service(self) -> Endpoints:
        """Endpoint сервиса."""
        return Endpoints.AGENCY_CLIENTS

    def change_offset(self, limited_by) -> None:
        """Меняет параметр offset в payload."""
        self.payload.change_offset(limited_by)

    def get(self):
        data = []
        has_all_clients_received = False
        while not has_all_clients_received:
            response = self.run_api_request()
            limited_by = response[self.RESULT_KEY].get(self.LIMITED_BY_KEY)
            data += response.get(self.RESULT_KEY).get('Clients')
            if limited_by:
                self.change_offset(limited_by)
            else:
                has_all_clients_received = True
        return data


class BaseReport(BaseApi):
    """
    Базовый класс для отчетов API Яндекс директ.\n
    Наследуется от BaseApi и переопределяет метод оркестратор run_api_request.
    """
    RETRY_IN_KEY = 'retryIn'
    RETRY_IN = 60
    INDENT = 4

    @property
    def endpoint_service(self) -> Endpoints:
        return Endpoints.REPORTS

    def run_api_request(self) -> Dict:
        """Оркестратор."""
        payload = self.get_payload()
        url = self.get_url()
        headers = self.get_headers()
        while True:
            response = self.api_request(url=url,
                                        headers=headers,
                                        payload=payload)
            if response.status_code == HTTPStatus.OK:
                # Отчет создан успешно
                response = self.api_response_decode(response)
                response = self.check_response(response)
                return response
            elif response.status_code == HTTPStatus.CREATED:
                # успешно поставлен в очередь в режиме offline
                retry_in = int(
                    response.headers.get(self.RETRY_IN_KEY, self.RETRY_IN)
                )
                sleep(retry_in)
            elif response.status_code == HTTPStatus.ACCEPTED:
                # Отчет формируется в режиме офлайн
                retry_in = int(
                    response.headers.get(self.RETRY_IN_KEY, self.RETRY_IN)
                )
                sleep(retry_in)
            else:
                raise exceptions.UnexpectedError(
                    f'endpoint: {self.endpoint_service} '
                    f'payload: {payload} ',
                    f'headers: {headers} ',
                    f'status_code: {self.status_code} ',
                )


class ClientCostReport(BaseReport):
    """
    Отчет затрат по клиенту.\n
    """

    COST_FIELD = 'Cost'
    CLICKS_FIELD = 'Clicks'

    def __init__(
            self,
            access_token: str,
            client_login: str,
            payload: Payload,
            on_sandbox: bool = False,
            language: str = 'ru'
    ):
        super().__init__(access_token, payload=payload,
                         on_sandbox=on_sandbox, language=language)
        self.client_login = client_login

    def get_headers(self) -> Dict[str, str]:
        headers = self.headers
        headers['Client-Login'] = self.client_login
        headers['skipReportHeader'] = 'true'
        headers['skipColumnHeader'] = 'true'
        headers['skipReportSummary'] = 'true'
        headers['returnMoneyInMicros'] = 'false'
        return headers

    def api_response_decode(self, response):
        response.encoding = 'utf-8'
        result = []
        if response.text:
            metrics = response.text.replace('\n', '\t').split('\t')
            fields = self.payload.get_fields()
            raw = {}
            i = 0
            for metric_id in range(0, len(metrics)):
                if i > len(fields) - 1:
                    result.append(raw)
                    raw = {}
                    i = 0
                current_field = fields[i]
                raw[current_field] = metrics[metric_id]
                i += 1
        return {'result': result}


class Campaigns(BaseApi):
    RESULT_KEY = 'result'
    LIMITED_BY_KEY = 'LimitedBy'

    def __init__(
            self,
            access_token: str,
            payload: Payload,
            client_login: str,
            on_sandbox: bool = False
    ):
        super().__init__(access_token=access_token,
                         payload=payload,
                         on_sandbox=on_sandbox)
        self.client_login = client_login

    @property
    def endpoint_service(self) -> Endpoints:
        return Endpoints.CAMPAIGNS

    def get_headers(self) -> Dict[str, str]:
        headers = super().get_headers()
        headers['Client-Login'] = self.client_login
        return headers

    def get(self):
        data = []
        has_all_clients_received = False
        while not has_all_clients_received:
            response = self.run_api_request()
            limited_by = response[self.RESULT_KEY].get(self.LIMITED_BY_KEY)
            data += response.get(self.RESULT_KEY).get('Campaigns')
            if limited_by:
                self.payload.change_offset(limited_by)
            else:
                has_all_clients_received = True
        return data


if __name__ == '__main__':
    ...

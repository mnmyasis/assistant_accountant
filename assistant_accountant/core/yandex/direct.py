import json
from time import sleep
from typing import List, Dict, Union

import requests
from http import HTTPStatus
from requests import Response

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
            field_names: List[str],
            selection_criteria: Dict = None,
            on_sandbox=False,
            language='ru'
    ):
        if selection_criteria is None:
            selection_criteria = dict()
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

    def get_method(self) -> Union[str, None]:
        """Возвращает метод запроса get, post, None."""
        ...

    def set_method(self, method: str, payload: Dict) -> Dict:
        """Устанавливает метод запроса в payload."""
        payload['method'] = method
        return payload

    def set_params(self, additional_payload_params, payload) -> Dict:
        """Установка дополнительных параметров."""
        for params in additional_payload_params:
            for key, value in params.items():
                if not key or not value:
                    raise ValueError(
                        f'{key}: {value}'
                    )
                payload[self.PARAMS_KEY][key] = value
        return payload

    def additional_payload_params(self) -> List[Dict]:
        """
        Для установки дополнительных параметров в дочерних классах,
        необходимо переопределить и вернуть список словарей с параметрами
        запроса.\n
        Пример:
        ----------
        @property\n
        def additional_payload_params(self) -> List[Dict]:
            return [
                {'ContractFieldNames': ['Price',]},
                {
                    'Page': {
                        'Limit': LIMIT,
                        'Offset': OFFSET
                    }
                },
            ]
        """
        ...

    def set_payload(self, payload: Dict) -> Dict:
        """Устанавливает дополнительные данные в запрос."""
        if self.get_method():
            payload = self.set_method(self.get_method(), payload)
        if self.additional_payload_params():
            payload = self.set_params(
                self.additional_payload_params(),
                payload)
        return payload

    def get_payload(self) -> Dict:
        """
        Возвращает payload.
        :return:payload
        """
        payload = {
            self.PARAMS_KEY: {
                "SelectionCriteria": self.selection_criteria,
                "FieldNames": self.field_names,
            }
        }
        return payload

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
            json.dumps(payload),
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
            payload: Dict
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
        payload = self.set_payload(payload)
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
                selection_criteria=...,\n
                field_names=...,\n
                on_sandbox=False,\n
                language='ru').get()
    """
    ENDPOINT = 'agencyclients'
    LIMIT = 2000
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
    METHOD = 'get'

    @property
    def endpoint_service(self) -> str:
        """Endpoint сервиса."""
        return self.ENDPOINT

    def additional_payload_params(self) -> List[Dict]:
        return [
            self.CONTRACT_FIELD_NAMES,
            self.PAGINATION_PARAMS,
        ]

    def get_method(self) -> Union[str, None]:
        return self.METHOD

    def change_offset(self, limited_by) -> None:
        """Меняет параметр offset в payload."""
        self.OFFSET = limited_by

    def get(self):
        data = []
        has_all_clients_received = False
        while not has_all_clients_received:
            response = self.run_api_request()
            limited_by = response[self.RESULT_KEY].get(self.LIMITED_BY_KEY)
            data.append(response.get(self.RESULT_KEY).get('Clients'))
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
    ENDPOINT = 'reports'
    RETRY_IN_KEY = 'retryIn'
    RETRY_IN = 60
    INDENT = 4

    @property
    def endpoint_service(self) -> str:
        return self.ENDPOINT

    def get_response(self, url, payload, headers) -> Response:
        return requests.post(
            url,
            json.dumps(payload, indent=self.INDENT),
            headers=headers)

    def run_api_request(self) -> Dict:
        """Оркестратор."""
        payload = self.get_payload()
        payload = self.set_payload(payload)
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
                    f'endpoint: {self.ENDPOINT} '
                    f'payload: {payload} ',
                    f'headers: {headers} ',
                    f'status_code: {self.status_code} ',
                )


class ClientCostReport(BaseReport):
    """
    Отчет затрат по клиенту.\n
    """
    REPORT_TYPE = 'ACCOUNT_PERFORMANCE_REPORT'
    REPORT_NAME = 'ACCOUNT_COST'
    FORMAT = 'TSV'
    INCLUDE_VAT = 'NO'
    INCLUDE_DISCOUNT = 'NO'
    COST_FIELD = 'Cost'
    CLICKS_FIELD = 'Clicks'
    FIELD_NAMES = [COST_FIELD, CLICKS_FIELD]

    def __init__(
            self,
            access_token: str,
            client_login: str,
            on_sandbox: bool = False,
            language: str = 'ru'
    ):
        super().__init__(access_token, self.FIELD_NAMES,
                         on_sandbox=on_sandbox, language=language)
        self.client_login = client_login

    def additional_payload_params(self) -> List[Dict]:
        return [
            {
                'ReportName': self.REPORT_NAME,
                'ReportType': self.REPORT_TYPE,
                'DateRangeType': 'AUTO',
                'Format': self.FORMAT,
                'IncludeVAT': self.INCLUDE_VAT,
                'IncludeDiscount': self.INCLUDE_DISCOUNT
            }
        ]

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
        result = {}
        if response.text:
            temp_result = response.text.split('\t')
            keys = self.FIELD_NAMES
            for key, value in zip(keys, temp_result):
                if key == self.COST_FIELD:
                    value = float(value)
                if key == self.CLICKS_FIELD:
                    value = int(value)
                result[key] = value
        return result


class Campaigns(BaseApi):
    ENDPOINT = 'campaigns'
    METHOD = 'get'
    RESULT_KEY = 'result'
    LIMITED_BY_KEY = 'LimitedBy'
    LIMIT = 10000
    OFFSET = 0
    PAGINATION_PARAMS = {
        'Page': {
            'Limit': LIMIT,
            'Offset': OFFSET
        }
    }

    def __init__(
            self,
            access_token: str,
            field_names: List[str],
            client_login: str
    ):
        super().__init__(access_token=access_token, field_names=field_names)
        self.client_login = client_login

    @property
    def endpoint_service(self) -> str:
        return self.ENDPOINT

    def get_headers(self) -> Dict[str, str]:
        headers = super().get_headers()
        headers['Client-Login'] = self.client_login
        return headers

    def get_method(self) -> Union[str, None]:
        return self.METHOD

    def additional_payload_params(self) -> List:
        return [
            self.PAGINATION_PARAMS
        ]

    def get(self):
        data = []
        has_all_clients_received = False
        while not has_all_clients_received:
            response = self.run_api_request()
            limited_by = response[self.RESULT_KEY].get(self.LIMITED_BY_KEY)
            data.append(response.get(self.RESULT_KEY).get('Campaigns'))
            if limited_by:
                self.OFFSET = limited_by
            else:
                has_all_clients_received = True
        return data


if __name__ == '__main__':
    ...

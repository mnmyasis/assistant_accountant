from typing import Dict, List
from http import HTTPStatus

import requests

from . import exceptions


class BaseApi:
    """
    Базовый класс для работы с API MyTarget.
    """

    HOST = 'target.my.com'
    VERSION = 'v2'
    TOKEN_LIMIT_ERROR = 'token_limit_exceeded'
    INVALID_TOKEN = 'invalid_token'
    EXPIRED_TOKEN = 'expired_token'
    HTTP_METHOD = 'get'

    @property
    def endpoint(self):
        """Endpoint сервиса api."""
        raise NotImplementedError

    def get_url(self) -> str:
        """Формирует урл."""
        return f'https://{self.HOST}/api/{self.VERSION}/{self.endpoint}'

    def get_headers(self) -> Dict:
        """Возвращает словарь с загололвками http запроса."""
        ...

    def get_params(self) -> Dict:
        """Возвращает параметры http запроса."""
        ...

    def get_data(self) -> Dict:
        """Возвращает данные для post запроса."""
        ...

    def send_response(
            self, url: str,
            params: Dict,
            headers: Dict = None,
            data: Dict = None,
    ) -> requests.Response:
        """Отправка http запроса."""
        if self.HTTP_METHOD == 'get':
            response = requests.get(url, params=params, headers=headers)
        elif self.HTTP_METHOD == 'post':
            response = requests.post(url, data=data,
                                     params=params, headers=headers)
        else:
            raise exceptions.MyTargetUnknownHttpMethod(
                f'Unknown method: {self.HTTP_METHOD}'
            )
        return response

    def response_api_errors_processing(self, response):
        """Проверка ошибок API."""
        response_error = response.json()
        error = response_error.get('error')
        code = error.get('code')
        if error == self.TOKEN_LIMIT_ERROR:
            raise exceptions.MyTargetTokenLimitError(response_error)
        if code == self.INVALID_TOKEN:
            raise exceptions.MyTargetInvalidTokenError(response_error)
        if code == self.EXPIRED_TOKEN:
            raise exceptions.MyTargetExpiredTokenError(response_error)
        raise exceptions.MyTargetOtherError(
            (f'error: {response_error} '
             f'url: {self.get_url()} '
             f'status_code: {response.status_code} '
             f'headers: {response.headers} '
             f'params: {self.get_params()}'
             f'data: {self.get_data()}')
        )

    def response_code_processing(self, response: requests.Response):
        """Проверка статус кодов ответа."""
        if response.status_code == HTTPStatus.OK:
            return
        if response.status_code in (
                HTTPStatus.FORBIDDEN,
                HTTPStatus.UNAUTHORIZED
        ):
            self.response_api_errors_processing(response)
        try:
            response.raise_for_status()
        except Exception as error:
            raise exceptions.MyTargetOtherError(error)

    def response_to_json(self, response: requests.Response) -> Dict:
        """Формирует из ответа словарь."""
        return response.json()

    def api_request(self) -> Dict:
        """Оркестратор."""
        url = self.get_url()
        headers = self.get_headers()
        data = self.get_data()
        params = self.get_params()
        response = self.send_response(
            url=url,
            params=params,
            headers=headers,
            data=data
        )
        self.response_code_processing(response)
        data = self.response_to_json(response)
        return data

    def run(self):
        """Интерфейс."""
        return self.api_request()


class AgencyClients(BaseApi):
    """
    Получение клиентов рекламного агентства.
    https://target.my.com/doc/api/ru/resource/AgencyClients
    """
    ENDPOINT = 'agency/clients.json'
    OFFSET = 0

    def __init__(self, access_token: str, limit: int = 50):
        self.access_token = access_token
        self.limit = limit

    @property
    def endpoint(self) -> str:
        return self.ENDPOINT

    def get_headers(self) -> Dict:
        return {
            'Authorization': f'Bearer {self.access_token}'
        }

    def get_params(self) -> Dict:
        return {
            'limit': self.limit,
            'offset': self.OFFSET
        }

    def run(self):
        items = []
        while True:
            response = self.api_request()
            item = response.get('items')
            if not item:
                break
            items += item
            self.OFFSET += self.limit
        return items


class SummaryStatistic(BaseApi):
    """
    Возвращает суммарную за все время открутки или подневную за выбранный
    период статистику по аккаунтам.
    https://target.my.com/doc/api/ru/info/Statistics

    date_from YYYY-MM-DD
    date_to YYYY-MM-DD
    ids	список идентификаторов
    """
    ENDPOINT = 'statistics/users/summary.json'

    def __init__(
            self,
            access_token: str,
            clients_id: List[int],
            date_from: str,
            date_to: str
    ):
        self.access_token = access_token
        self.clients_id = clients_id
        self.date_from = date_from
        self.date_to = date_to

    @property
    def endpoint(self):
        return self.ENDPOINT

    def get_headers(self) -> Dict:
        return {'Authorization': f'Bearer {self.access_token}'}

    def get_params(self) -> Dict:
        return {
            'metrics': 'base',
            'id': self.clients_id,
            'date_from': self.date_from,
            'date_to': self.date_to
        }


class DayStatistic(SummaryStatistic):
    ENDPOINT = 'statistics/users/day.json'

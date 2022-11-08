from typing import Dict

import requests

from . import exceptions


class BaseApi:
    """Базовый класс VK API."""
    API_VERSION = '5.131'
    API_URL = 'https://api.vk.com/method/'

    FLOOD_ERROR_CODE = 9
    MANY_REQUEST_PER_SECOND_ERROR_CODE = 6
    REQUEST_TIMEOUT = 1

    def __init__(self, access_token: str):
        self.access_token = access_token

    @property
    def api_method(self) -> str:
        """Метод API VK."""
        raise NotImplementedError

    def get_api_version(self) -> str:
        """Возвращает версию API."""
        return self.API_VERSION

    def get_params(self) -> Dict:
        """Возвращает параметры запроса."""
        return {
            'access_token': self.access_token,
            'v': self.get_api_version()
        }

    def get_url(self) -> str:
        """Формирует урл для запроса к API."""
        return self.API_URL + self.api_method

    def send_request(self, url: str, params: Dict) -> requests.Response:
        """Отправка http запроса."""
        response = requests.get(url, params=params)
        return response

    def dict_converting(self, response: requests.Response) -> Dict:
        """Преобразование в Dict."""
        return response.json()

    def get_response(self, url: str, params: Dict) -> requests.Response:
        """Возвращает ответ от API."""
        try:
            response = self.send_request(url, params)
            response.raise_for_status()
        except Exception as error:
            raise exceptions.VkRequestError(error)
        return response

    def error_checking(self, data: Dict) -> Dict:
        """Проверка овета от API на ошибки."""
        error = data.get('error')
        if error:
            error_code = error.get('error_code')
            if error_code == self.FLOOD_ERROR_CODE:
                raise exceptions.VkFloodControlError()
            elif error_code == self.MANY_REQUEST_PER_SECOND_ERROR_CODE:
                raise exceptions.VkManyRequestPerSecondError()
            else:
                raise exceptions.VkDataError(error)
        return data

    def run(self):
        """Метод оркестратор."""
        url = self.get_url()
        params = self.get_params()
        response = self.get_response(url, params)
        data = self.dict_converting(response)
        data = self.error_checking(data)
        return data

    def get(self):
        """Интерфейс."""
        return self.run()


class Account(BaseApi):
    """Список рекламных аккаунтов. https://dev.vk.com/method/ads.getAccounts"""

    METHOD = 'ads.getAccounts'

    @property
    def api_method(self) -> str:
        return self.METHOD


class Clients(BaseApi):
    """Список клиентов агентства. https://dev.vk.com/method/ads.getClients"""

    METHOD = 'ads.getClients'

    def __init__(self, access_token: str, account_id: int):
        super().__init__(access_token)
        self.account_id = account_id

    @property
    def api_method(self) -> str:
        return self.METHOD

    def get_params(self) -> Dict:
        params = super().get_params()
        params['account_id'] = self.account_id
        return params


class Statistic(BaseApi):
    """
    Сбор статистики.
    https://dev.vk.com/method/ads.getStatistics

    ids_type тип запрашиваемых объектов, которые перечислены в параметре:\n
    ad — объявления; \n
    campaign — кампании; \n
    client — клиенты; \n
    office — кабинет.

    period способ группировки данных по датам:\n
    day — статистика по дням; \n
    week — статистика по неделям; \n
    month — статистика по месяцам; \n
    year — статистика по годам; \n
    overall — статистика за всё время; \n

    date_from, date_to используется разный формат дат для разного значения
    параметра period:\n
    day: YYYY-MM-DD, пример: 2011-09-27 - 27 сентября 2011. \n
    week: YYYY-MM-DD, пример: 2011-09-27 - считаем статистику, начиная с
    понедельника той недели, в которой находится заданный день. \n
    month: YYYY-MM, пример: 2011-09 - сентябрь 2011. \n
    year: YYYY, пример: 2011 - 2011 год. \n
    overall: 0 \n
    """
    METHOD = 'ads.getStatistics'
    MAX_IDS = 2000

    def __init__(
            self,
            access_token: str,
            account_id: str,
            ids: list,
            date_from: str,
            date_to: str,
            ids_type: str = 'client',
            period: str = 'year',
    ):
        super().__init__(access_token)
        self.account_id = account_id
        self.ids = ids
        self.date_from = date_from
        self.date_to = date_to
        self.ids_type = ids_type
        self.period = period

    @property
    def api_method(self) -> str:
        return self.METHOD

    def get_params(self) -> Dict:
        params = super().get_params()
        params['account_id'] = self.account_id
        if len(self.ids) > self.MAX_IDS:
            raise exceptions.VkStatisticMaxObjectError(
                f'Object limit exceeded: {len(self.ids)} > {self.MAX_IDS}'
            )
        params['ids'] = ','.join([str(x) for x in self.ids])
        params['ids_type'] = self.ids_type
        params['date_from'] = self.date_from
        params['date_to'] = self.date_to
        params['period'] = self.period
        return params


class GetBudget(BaseApi):
    """Возвращает текущий бюджет рекламного кабинета."""
    METHOD = 'ads.getBudget'

    def __init__(self, access_token: str, account_id: str):
        super().__init__(access_token)
        self.account_id = account_id

    @property
    def api_method(self) -> str:
        return self.METHOD

    def get_params(self) -> Dict:
        params = super().get_params()
        params['account_id'] = self.account_id
        return params

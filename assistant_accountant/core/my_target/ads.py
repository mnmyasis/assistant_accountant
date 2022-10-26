from typing import Dict, Tuple
from http import HTTPStatus

import requests

from . import exceptions


class BaseApi:
    HOST = 'target.my.com'
    VERSION = 'v2'
    TOKEN_LIMIT_ERROR = 'token_limit_exceeded'
    INVALID_TOKEN = 'invalid_token'
    EXPIRED_TOKEN = 'expired_token'
    HTTP_METHOD = 'get'

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    @property
    def endpoint(self):
        raise NotImplementedError

    def get_url(self):
        return f'https://{self.HOST}/api/{self.VERSION}/{self.endpoint}'

    def get_headers(self) -> Dict:
        ...

    def get_params(self) -> Dict:
        ...

    def get_data(self) -> Dict:
        ...

    def send_response(
            self, url: str,
            params: Dict,
            headers: Dict = None,
            data: Dict = None,
    ) -> requests.Response:
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

    def response_code_processing(self, response: requests.Response):
        response_json = self.response_to_json(response)
        if response.status_code == HTTPStatus.FORBIDDEN:
            error = response_json.get('error')
            if error == self.TOKEN_LIMIT_ERROR:
                raise exceptions.MyTargetTokenLimitError(response_json)
            raise exceptions.MyTargetOtherError(response_json)
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            code = response_json.get('code')
            if code == self.INVALID_TOKEN:
                raise exceptions.MyTargetInvalidTokenError(response_json)
            if code == self.EXPIRED_TOKEN:
                raise exceptions.MyTargetExpiredTokenError(response_json)
            raise exceptions.MyTargetOtherError(response_json)
        try:
            response.raise_for_status()
        except Exception as error:
            raise exceptions.MyTargetOtherError(error)

    def response_to_json(self, response: requests.Response) -> Dict:
        return response.json()

    def api_request(self) -> Dict:
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
        return self.api_request()

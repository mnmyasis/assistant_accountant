import json

import requests

from http import HTTPStatus

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
            raise exceptions.YandexDirectApiRequestERROR(
                f'Код ответа API: {response.status_code}, '
                f'RequestId: {response.headers.get("RequestId")}, '
                f'Ответ: {error}, '
                f'endpoint: {url}'
            )
        if not response_json['result']:
            print(data)
            return data
        if response_json['result'].get("LimitedBy", False):
            agency_client_body['Page']['Offset'] = response_json['result'][
                "LimitedBy"]
        data.append(response_json)


if __name__ == '__main__':
    print(get_url())

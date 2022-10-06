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


if __name__ == '__main__':
    pass

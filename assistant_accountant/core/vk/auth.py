import requests

from . import exceptions

AUTH_URL = 'https://oauth.vk.com/authorize'
ACCESS_TOKEN_URL = 'https://oauth.vk.com/access_token'
API_VERSION = '5.131'


def get_auth_url(
        client_id: str,
        redirect_uri: str,
        display: str = 'page',
        scope: str = 'ads,offline',
        response_type: str = 'code',
        state: str = None
):
    """
    Формирует урл для открытия диалога авторизации.\n

    Варианты значений display:\n
    page — форма авторизации в отдельном окне;\n
    popup — всплывающее окно;\n
    mobile — авторизация для мобильных устройств (без использования Javascript)
    Если пользователь авторизуется с мобильного устройства, будет использован
    тип mobile.\n

    :param client_id: идентификатор приложения.
    :param redirect_uri: адрес, на который будет передан code
    :param display: указывает тип отображения страницы авторизации.
    :param scope: настройки доступа, которые необходимо проверить при
                  авторизации пользователя и запросить отсутствующие
                  (значение offline означает, что запрашиваемый токен
                  бессрочный.)
    :param response_type: тип ответа, который вы хотите получить (укажите code)
    :param state: произвольная строка, будет возвращена вместе с результатом
                  авторизации
    :return: auth_url
    """
    auth_url = (
        f'{AUTH_URL}?client_id={client_id}&display={display}&'
        f'redirect_uri={redirect_uri}&scope={scope}&'
        f'response_type={response_type}&v={API_VERSION}&state={state}'
    )
    return auth_url


def get_access_token(
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        code: str
):
    """
    Получение acess_token.\n

    :param client_id: идентификатор вашего приложения
    :param client_secret: защищенный ключ вашего приложения
    :param redirect_uri: URL, который использовался при получении code на
                         первом этапе авторизации
    :param code: временный код, полученный после прохождения авторизации.
    :return: access_token, expires_in
    """
    try:
        response = requests.get(ACCESS_TOKEN_URL, params={
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'code': code
        })
        response_json = response.json()
        if response_json.get('error'):
            raise exceptions.VkRequestError(response_json)
        response.raise_for_status()
    except Exception as error:
        raise exceptions.VkRequestError(error)

    access_token = response_json.get('access_token')
    expires_in = response_json.get('expires_in')
    if not access_token:
        raise exceptions.VkRequestError('Missing access token.')
    if expires_in is None or not isinstance(expires_in, int):
        raise exceptions.VkRequestError(
            f'Missing expires_in or data type is not int: {expires_in}'
        )
    return access_token, expires_in

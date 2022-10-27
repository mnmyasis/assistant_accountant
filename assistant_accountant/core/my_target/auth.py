from typing import Dict

from .ads import BaseApi


class BaseAuth(BaseApi):
    """
    Базовый класс для работы с токенами.
    https://target.my.com/doc/api/ru/info/ApiAuthorization
    """
    HTTP_METHOD = 'post'

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    @property
    def endpoint(self):
        raise NotImplementedError()

    def get_url(self) -> str:
        return f'https://{self.HOST}/api/{self.VERSION}/oauth2/{self.endpoint}'


class ClientCredentialsToken(BaseAuth):
    """
    Получение access_token.
    Client Credentials Grant используется для работы с данными собственного
    аккаунта через API.
    CreateToken(client_id, client_secret).run()
    """

    GRANT_TYPE = 'client_credentials',
    ENDPOINT = 'token.json'

    @property
    def endpoint(self):
        return self.ENDPOINT

    def get_data(self) -> Dict:
        return {
            'grant_type': self.GRANT_TYPE,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }


class DeleteTokens(BaseAuth):
    """
    Удаление токенов пользователя.
    DeleteTokens(client_id, client_secret, user_id).run()
    """
    ENDPOINT = 'token/delete.json'

    def __init__(self, client_id: str, client_secret: str, user_id: int):
        super().__init__(client_id, client_secret)
        self.user_id = user_id

    @property
    def endpoint(self):
        return self.ENDPOINT

    def get_data(self) -> Dict:
        return {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'user_id': self.user_id
        }

    def api_request(self) -> Dict[str, bool]:
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
        return {'is_deleted': True}


class RefreshToken(BaseAuth):
    """
    Обновление токена.
    RefreshToken(client_id, client_secret, refresh_token).run()
    """
    ENDPOINT = 'token.json'
    GRANT_TYPE = 'refresh_token'

    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        super().__init__(client_id, client_secret)
        self.refresh_token = refresh_token

    @property
    def endpoint(self):
        return self.ENDPOINT

    def get_data(self) -> Dict:
        return {
            'grant_type': self.GRANT_TYPE,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token
        }

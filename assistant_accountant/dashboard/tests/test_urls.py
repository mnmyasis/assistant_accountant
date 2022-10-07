from http import HTTPStatus
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse

from dashboard.models import User


class DashboardTest(TestCase):
    YANDEX_DIRECT_CALLBACK_URL = reverse('dashboard:yandex_direct_callback')

    PRIVATE_URLS = [
        reverse('dashboard:index'),
    ]

    REDIRECT_URLS = [
        YANDEX_DIRECT_CALLBACK_URL
    ]
    EXPIRES_IN = 666
    ACCESS_TOKEN = 'qwe'
    REFRESH_TOKEN = 'ewq'
    YANDEX_DIRECT_API_TOKEN = {
        'access_token': ACCESS_TOKEN,
        'refresh_token': REFRESH_TOKEN,
        'expires_in': EXPIRES_IN
    }
    USER1 = 'user1'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1 = User.objects.create_user(cls.USER1)

    def setUp(self) -> None:
        self.guest_user = Client()
        self.auth_user = Client()
        self.auth_user.force_login(self.user1)

    def test_redirect_private_urls(self):
        for url in self.PRIVATE_URLS:
            with self.subTest(url=url):
                response = self.guest_user.get(url)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_private_urls(self):
        for url in self.PRIVATE_URLS:
            with self.subTest(url=url):
                response = self.auth_user.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    @patch('core.yandex.direct.exchange_code_on_token')
    def test_yandex_callback(
            self,
            mock_exchange_code_on_token
    ):
        args = {'code': 123}
        mock_exchange_code_on_token.return_value = self.YANDEX_DIRECT_API_TOKEN
        response = self.auth_user.get(self.YANDEX_DIRECT_CALLBACK_URL, args)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        response = self.guest_user.get(self.YANDEX_DIRECT_CALLBACK_URL, args)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)


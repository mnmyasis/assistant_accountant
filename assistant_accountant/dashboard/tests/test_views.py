from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse

from dashboard.models import User, YandexDirectToken


class ContextViewTest(TestCase):
    TEST_USER1 = 'user1'
    EXPIRES_IN = 666
    ACCESS_TOKEN = 'qwe'
    REFRESH_TOKEN = 'ewq'
    YANDEX_DIRECT_API_TOKEN = {
        'access_token': ACCESS_TOKEN,
        'refresh_token': REFRESH_TOKEN,
        'expires_in': EXPIRES_IN
    }
    YANDEX_DIRECT_VERIFICATION_CODE = 123
    EXPECTED_COUNT_TOKENS = 1

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(cls.TEST_USER1)

    def setUp(self) -> None:
        self.auth_client = Client()
        self.auth_client.force_login(self.user)

    def test_content_index(self):
        """Проверка контекста view index."""
        response = self.auth_client.get(reverse('dashboard:index'))
        self.assertIsNotNone(
            response.context['yandex_direct_verification_code_url']
        )

    @patch('core.yandex.direct.exchange_code_on_token')
    def test_create_token_yandex_direct_callback(
            self,
            mock_exchange_code_on_token
    ):
        """Проверка создания токена view yandex_direct_callback."""
        mock_exchange_code_on_token.return_value = self.YANDEX_DIRECT_API_TOKEN
        self.auth_client.get(
            reverse('dashboard:yandex_direct_callback'),
            {'code': self.YANDEX_DIRECT_VERIFICATION_CODE}
        )
        ya_token = YandexDirectToken.objects.filter(
            user=self.user)

        self.assertEqual(len(ya_token), self.EXPECTED_COUNT_TOKENS,
                         msg='Создался лишний токен.')
        self.assertEqual(ya_token[0].user, self.user)
        self.assertEqual(ya_token[0].access_token, self.ACCESS_TOKEN)
        self.assertEqual(ya_token[0].refresh_token, self.REFRESH_TOKEN)
        self.assertEqual(ya_token[0].expires_in, self.EXPIRES_IN)

    @patch('core.yandex.direct.exchange_code_on_token')
    def test_update_token_yandex_direct_callback(
            self,
            mock_exchange_code_on_token
    ):
        """Проверка обновления токена view yandex_direct_callback."""
        YandexDirectToken.objects.create(
            user=self.user,
            access_token='jeqrutrqiuty132',
            refresh_token=self.REFRESH_TOKEN,
            expires_in=self.EXPIRES_IN
        )
        mock_exchange_code_on_token.return_value = self.YANDEX_DIRECT_API_TOKEN
        self.auth_client.get(
            reverse('dashboard:yandex_direct_callback'),
            {'code': self.YANDEX_DIRECT_VERIFICATION_CODE}
        )
        ya_token = YandexDirectToken.objects.filter(
            user=self.user)
        self.assertEqual(len(ya_token), self.EXPECTED_COUNT_TOKENS,
                         msg='При обновлении создался лишний токен.')
        self.assertEqual(ya_token[0].access_token, self.ACCESS_TOKEN,
                         msg='Токен не обновился.')

    @patch('core.yandex.direct.exchange_code_on_token')
    def test_raise_exceptions_yandex_direct_callback(
            self,
            mock_exchange_code_on_token
    ):
        """Проверка на исключения view yandex_direct_callback."""
        api_answers = [
            {
                'access_token': None,
                'refresh_token': self.REFRESH_TOKEN,
                'expires_in': self.EXPIRES_IN
            },
            {
                'access_token': self.ACCESS_TOKEN,
                'refresh_token': None,
                'expires_in': self.EXPIRES_IN
            },
            {
                'access_token': self.ACCESS_TOKEN,
                'refresh_token': self.REFRESH_TOKEN,
                'expires_in': None
            },
            {
                'access_token': self.ACCESS_TOKEN,
                'refresh_token': self.REFRESH_TOKEN,
                'expires_in': '123'
            },
        ]
        expected_raises = [
            ValueError,
            ValueError,
            TypeError,
            TypeError
        ]

        for api_answer, expected_raise in zip(api_answers, expected_raises):
            with self.subTest(api_answer):
                mock_exchange_code_on_token.return_value = api_answer
                try:
                    self.auth_client.get(
                        reverse('dashboard:yandex_direct_callback'),
                        {'code': self.YANDEX_DIRECT_VERIFICATION_CODE}
                    )
                except Exception as error:
                    self.assertIsInstance(error, expected_raise,
                                          msg='Непредвиденное исключение.')

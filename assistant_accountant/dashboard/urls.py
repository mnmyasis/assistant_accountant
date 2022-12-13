from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('yandex-direct-callback',
         views.yandex_direct_callback,
         name='yandex_direct_callback'),
    path('vk-callback', views.vk_callback),
    path('yandex-direct/test/', views.yandex_test, name='yandex_test'),
    path('vk/test/', views.vk_test, name='vk_test'),
    path('my-target/auth', views.my_target_auth, name='my_target_auth'),
    path('my-target/test', views.my_target_test, name='my_target_test'),
    path('sheet', views.sheets_view, name='sheets_view'),
    path('test', views.test)
]

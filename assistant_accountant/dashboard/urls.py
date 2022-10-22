from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('yandex-direct-callback',
         views.yandex_direct_callback,
         name='yandex_direct_callback'),
    path('yandex-direct/test/', views.yandex_test, name='yandex_test')
]

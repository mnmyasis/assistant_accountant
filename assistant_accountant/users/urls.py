from django.urls import path
from django.contrib.auth.views import (LogoutView,
                                       LoginView, )

app_name = 'users'

urlpatterns = [
    path('logout/', LogoutView.as_view(), name='logout'),
    path('login/',
         LoginView.as_view(template_name='users/login.html'),
         name='login'),
]

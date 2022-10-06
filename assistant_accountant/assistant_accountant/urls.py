from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('about.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('accounts/', include('users.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]

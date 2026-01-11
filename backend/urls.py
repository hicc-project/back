"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from cafes.views import places,collect_places, collect_details, refresh_status, cafes_24h, open_status_logs

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/places/", places),
    path("api/collect/", collect_places),
    path("collect_details/", collect_details),
    path("refresh_status/", refresh_status),
    path("api/cafes_24h/", cafes_24h),
    path("api/open_status_logs/", open_status_logs),
]

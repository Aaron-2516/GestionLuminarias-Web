from django.urls import path

from django.contrib import admin

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', views.dashboard, name='dashboard'),
]

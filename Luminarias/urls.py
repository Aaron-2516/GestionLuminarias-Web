from django.urls import path

from django.contrib import admin

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard_supervisor/', views.dashboard_supervisor, name='dashboard_supervisor'),
    path('agregar_tecnicos/', views.agregar_tecnicos, name='agregar_tecnicos'),
    path('agregar_redes/', views.agregar_redes, name='agregar_redes'),
    path('base_supervisor/', views.base_supervisor, name='base_supervisor'),
    path('base_tecnicos/', views.base_tecnicos, name='base_tecnicos'),
]

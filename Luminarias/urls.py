from django.urls import path

from django.contrib import admin

from . import views

urlpatterns = [
    path("", views.login_view, name="home"),
    path("login/", views.login_view, name="login"),
    path('admin/', admin.site.urls),
    path('dashboard_supervisor/', views.dashboard_supervisor, name='dashboard_supervisor'),
    path('dashboard_tecnico/', views.dashboard_tecnico, name='dashboard_tecnico'),
    path('agregar_tecnicos/', views.agregar_tecnicos, name='agregar_tecnicos'),
    path('agregar_redes/', views.agregar_redes, name='agregar_redes'),
    path('base_supervisor/', views.base_supervisor, name='base_supervisor'),
    path('base_tecnicos/', views.base_tecnicos, name='base_tecnicos'),
#    path('redes/', views.redes, name='redes'),         # ← faltaba
 #   path('zonas/', views.zonas, name='zonas'),         # ← faltaba
  #  path('luminarias/', views.luminarias, name='luminarias'),  # ← faltaba
]

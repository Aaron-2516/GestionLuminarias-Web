from django.urls import path

from . import views

urlpatterns = [
    path("", views.login_view, name="home"),
    path("login/", views.login_view, name="login"),
    path("dashboard_supervisor/", views.dashboard_supervisor, name="dashboard_supervisor"),
    path("dashboard_tecnico/", views.dashboard_tecnico, name="dashboard_tecnico"),
    path("agregar_tecnicos/", views.agregar_tecnicos, name="agregar_tecnicos"),
    path("agregar_redes/", views.agregar_redes, name="agregar_redes"),
]

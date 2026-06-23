from django.urls import path

from . import views

urlpatterns = [
    path("", views.login_view, name="home"),
    path("login/", views.login_view, name="login"),
    path("cambiar_contrasena/", views.cambiar_contrasena, name="cambiar_contrasena"),
    path("cambiar_contrasena_primer_acceso/", views.cambiar_contrasena_primer_acceso, name="cambiar_contrasena_primer_acceso"),
    path("cerrar_sesion/", views.cerrar_sesion, name="cerrar_sesion"),
    path("dashboard_supervisor/", views.dashboard_supervisor, name="dashboard_supervisor"),
    path("dashboard_tecnico/", views.dashboard_tecnico, name="dashboard_tecnico"),
    path("agregar_tecnicos/", views.agregar_tecnicos, name="agregar_tecnicos"),
    path("agregar_redes/", views.agregar_redes, name="agregar_redes"),
    path("base/", views.base, name="base"),
    path("base_supervisor/", views.base_supervisor, name="base_supervisor"),
    path("base_tecnicos/", views.base_tecnicos, name="base_tecnicos"),
    path("generar_informe/", views.generar_informe, name="generar_informe"),
    path("registrar_lecturas/", views.registrar_lecturas, name="registrar_lecturas"),
    path("agregar_zonas/", views.agregar_zonas, name="agregar_zonas"),
    path("agregar_luminarias/", views.agregar_luminarias, name="agregar_luminarias"),
]

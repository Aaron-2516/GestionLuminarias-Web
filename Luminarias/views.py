from django.shortcuts import redirect, render

from .models import Usuario


def page_view(template_name):
    def view(request):
        return render(request, f"luminarias/{template_name}.html")

    view._name_ = template_name
    return view


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        try:
            usuario = Usuario.objects.select_related("rol").get(
                id_usuario=username,
                contrasena=password
            )
        except Usuario.DoesNotExist:
            return render(
                request,
                "luminarias/login.html",
                {"error": "Usuario o contrasena incorrectos."}
            )

        request.session["usuario_id"] = usuario.id_usuario
        request.session["usuario_nombre"] = usuario.nombre_usuario
        request.session["rol_id"] = usuario.rol_id

        if usuario.rol_id == 1:
            return redirect("dashboard_supervisor")

        if usuario.rol_id == 2:
            return redirect("dashboard_tecnico")

        return render(
            request,
            "luminarias/login.html",
            {"error": "El usuario no tiene un rol valido."}
        )

    return render(request, "luminarias/login.html")


def cambiar_contrasena(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password_actual = request.POST.get("password_actual", "")
        password_nueva = request.POST.get("password_nueva", "")
        confirmar_password = request.POST.get("confirmar_password", "")

        if password_nueva != confirmar_password:
            return render(
                request,
                "luminarias/cambiar_contrasena.html",
                {"error": "Las contrasenas nuevas no coinciden."}
            )

        try:
            usuario = Usuario.objects.get(
                id_usuario=username,
                contrasena=password_actual
            )
        except Usuario.DoesNotExist:
            return render(
                request,
                "luminarias/cambiar_contrasena.html",
                {"error": "Usuario o contrasena actual incorrectos."}
            )

        usuario.contrasena = password_nueva
        usuario.save(update_fields=["contrasena"])

        return render(
            request,
            "luminarias/login.html",
            {"success": "Contrasena actualizada correctamente. Inicia sesion."}
        )

    return render(request, "luminarias/cambiar_contrasena.html")


def cerrar_sesion(request):
    request.session.flush()
    return redirect("login")


dashboard_supervisor = page_view("dashboard_supervisor")
dashboard_tecnico = page_view("dashboard_tecnico")
agregar_tecnicos = page_view("agregar_tecnicos")
agregar_redes = page_view("agregar_redes")
base = page_view("base")
base_supervisor = page_view("base_supervisor")
base_tecnicos = page_view("base_tecnicos")

from django.shortcuts import render


def page_view(template_name):
    def view(request):
        return render(request, f"luminarias/{template_name}.html")

    view.__name__ = template_name
    return view


login_view = page_view("login")
dashboard_supervisor = page_view("dashboard_supervisor")
dashboard_tecnico = page_view("dashboard_tecnico")
agregar_tecnicos = page_view("agregar_tecnicos")
agregar_redes = page_view("agregar_redes")
base = page_view("base")
base_supervisor = page_view("base_supervisor")
base_tecnico = page_view("base_tecnico")

from django.shortcuts import render

def dashboard_supervisor(request):
    return render(request, 'Luminarias/dashboad_supervisor.html')

def agregar_tecnicos(request):
    return render(request, 'Luminarias/agregar_tecnicos.html')

def agregar_redes(request):
    return render(request, 'Luminarias/agregar_redes.html')

def base_supervisor(request):
    return render(request, 'Luminarias/base_supervisor.html')

def base_tecnicos(request):
    return render(request, 'Luminarias/base_tecnicos.html')

def login_view(request):

    return render(request,"luminarias/login.html"
    )




def dashboard_tecnico(request):


    return render(request,"luminarias/dashboard_tecnico.html"
    )


def redes(request):    
    return render(request, "luminarias/redes.html")


def zonas(request):
    return render(request, "luminarias/zonas.html")


def luminarias(request):
    return render(request, "luminarias/luminarias.html")


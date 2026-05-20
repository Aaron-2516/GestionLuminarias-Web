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


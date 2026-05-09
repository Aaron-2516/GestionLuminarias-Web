from django.shortcuts import render

def dashboard(request):
    return render(request, 'Luminarias/dashboard.html')

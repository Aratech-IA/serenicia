from django.shortcuts import render, redirect

# Page Index help
def index(request):
    return render(request, 'app17_help/index.html')
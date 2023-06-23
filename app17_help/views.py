from django.shortcuts import render, redirect

# Page Index help
def index(request):
    return render(request, 'app17_help/index.html')

# Page Social_life help
def social_life(request):
    return render(request, 'app17_help/social_life.html')
    
# Page Cuisine help
def cuisine(request):
    return render(request, 'app17_help/cuisine.html')
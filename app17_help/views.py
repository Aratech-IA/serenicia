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
    
# Page Hotel help
def hotel(request):
    return render(request, 'app17_help/hotel.html')
    
# Page Quality help
def quality(request):
    return render(request, 'app17_help/quality.html')
    
# Page referrers help
def referrers(request):
    return render(request, 'app17_help/referrers.html')
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, login_not_required

@login_not_required
def unloginpage(request):
    return render(request, 'main/unloginpage.html')

@login_required(login_url='/accounts/login/')
def home_page(request):
    if not request.user.is_authenticated:
        return redirect('main:unloginpage')
    return render(request, 'main/home.html')
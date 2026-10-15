"""
Module 4 Views: Login, Register, Logout (Role-based access).
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CampusUser


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard:home')
        messages.error(request, 'Invalid credentials.')

    return render(request, 'automation_auth/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        password   = request.POST.get('password', '')
        email      = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        role       = request.POST.get('role', 'student')
        department = request.POST.get('department', '').strip()

        if CampusUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
        else:
            user = CampusUser.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role,
                department=department,
            )
            login(request, user)
            messages.success(request, f'Welcome, {user.get_full_name()}!')
            return redirect('dashboard:home')

    return render(request, 'automation_auth/register.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('automation_auth:login')

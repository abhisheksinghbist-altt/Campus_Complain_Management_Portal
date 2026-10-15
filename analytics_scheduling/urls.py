from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('',           views.dashboard,         name='home'),
    path('schedule/',  views.scheduling_demo,   name='scheduling'),
]

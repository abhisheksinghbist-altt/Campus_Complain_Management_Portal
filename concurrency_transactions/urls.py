from django.urls import path
from . import views

app_name = 'concurrency_transactions'

urlpatterns = [
    path('<int:complaint_id>/', views.assign_ticket, name='assign'),
]

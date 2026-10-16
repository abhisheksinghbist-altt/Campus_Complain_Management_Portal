from django.urls import path
from . import views

app_name = "submission_monitoring"

urlpatterns = [
    path("submit/",                      views.submit_complaint, name="submit"),
    path("list/",                        views.complaint_list,   name="list"),
    path("detail/<int:complaint_id>/",   views.detail_complaint, name="detail"),
    path("rate/<int:complaint_id>/",     views.rate_complaint,   name="rate"),
    path("health/",                      views.health_check,     name="health_check"),
]

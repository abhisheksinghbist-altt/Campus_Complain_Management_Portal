from django.urls import path
from . import views

app_name = "status_caching"

urlpatterns = [
    path("my/",                        views.my_complaints,   name="my_complaints"),
    path("<int:complaint_id>/",        views.track_complaint, name="track"),
    path("update/<int:complaint_id>/", views.update_status,   name="update_status"),
    path("cache-stats/",               views.cache_stats,     name="cache_stats"),
]

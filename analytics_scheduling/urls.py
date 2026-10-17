from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("",                          views.dashboard,       name="home"),
    path("schedule/",                 views.scheduling_demo, name="scheduling"),
    path("bulk-assign/",              views.bulk_assign,     name="bulk_assign"),
    path("queue/",                    views.queue_processor, name="queue"),
    path("compare/",                  views.comparison,      name="compare"),
    path("smart-result/<int:complaint_id>/", views.smart_result, name="smart_result"),
]

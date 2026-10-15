from django.urls import path
from . import views

app_name = 'file_engine'

urlpatterns = [
    path('upload/<int:complaint_id>/', views.upload_attachment,  name='upload'),
    path('download/<int:attachment_id>/', views.download_attachment, name='download'),
]

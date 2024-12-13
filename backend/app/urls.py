# app/urls.py
from django.urls import path
from . import views  # Assuming your views are in the same app

urlpatterns = [
    path('fetch-video/', views.fetch_video_data, name='fetch-video'),
    path('download-video/', views.download_video, name='download-video'),
]

# backend/urls.py 
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

# A simple view for the root URL
def index(request):
    return HttpResponse("Welcome to the Django API!")

urlpatterns = [
    path('', index, name='home'),  # This serves the homepage (root)
    path('admin/', admin.site.urls),  # Admin URL
    path('api/', include('app.urls')),  # Include app URLs under /api
]

# Serve media files during development
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

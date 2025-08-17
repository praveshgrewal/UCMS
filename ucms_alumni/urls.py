"""ucms_alumni URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('alumni.urls')),
]

# Always serve MEDIA (uploads) via Django (okay for low traffic)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Only serve STATIC via Django in DEBUG; in prod WhiteNoise handles /static/
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

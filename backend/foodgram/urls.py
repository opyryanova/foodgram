from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from api.views import ShortLinkRedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("s/<str:code>/", ShortLinkRedirectView.as_view(), name="shortlink"),
    path("s/<str:code>", ShortLinkRedirectView.as_view()),
    path("api/auth/", include("djoser.urls")),
    path("api/auth/", include("djoser.urls.authtoken")),
    path("api/", include("api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT,
    )
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

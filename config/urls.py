from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from django.conf import settings

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # API
    path("api/", include("documents.urls")),
    # 3rd party
    # DRF
    path("api-auth/", include("rest_framework.urls")),
    # Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

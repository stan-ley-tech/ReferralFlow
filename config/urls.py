from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import HealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
    # Versioning is a plain URL prefix rather than DRF's URLPathVersioning:
    # that class injects a `version` kwarg into every view under the path,
    # which every custom @action method would then need to accept for no
    # benefit this project needs. A v2 API is added by pointing a second
    # prefix at a new urls module, not by touching v1.
    path("api/v1/", include("config.api_urls")),
]

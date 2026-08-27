import logging

from django.core.cache import cache
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("referralflow.health")


class HealthCheckView(APIView):
    """
    Liveness/readiness probe for orchestrators and uptime monitors. Verifies
    the database and cache backend are reachable rather than just returning
    a static 200, since a process that's up but can't reach Postgres or
    Redis is not actually healthy.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        checks = {
            "database": self._check_database(),
            "cache": self._check_cache(),
        }
        healthy = all(checks.values())
        status_code = 200 if healthy else 503
        return Response({"status": "ok" if healthy else "degraded", "checks": checks}, status=status_code)

    @staticmethod
    def _check_database():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            logger.exception("Database health check failed")
            return False

    @staticmethod
    def _check_cache():
        try:
            cache.set("health_check", "ok", timeout=5)
            return cache.get("health_check") == "ok"
        except Exception:
            logger.exception("Cache health check failed")
            return False

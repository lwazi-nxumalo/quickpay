from django.db import connection
from django.http import JsonResponse


def health(request):
    """Public liveness check: Railway's healthcheck and a cheap way to wake the service.

    Runs one trivial query so a healthy answer also means the database is reachable.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})

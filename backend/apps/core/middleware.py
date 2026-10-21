from django.conf import settings
from django.core.exceptions import BadRequest, PermissionDenied, SuspiciousOperation
from django.http import Http404
from .errors import capture_body, new_code, record
from .views import error_response


class ErrorTrackingMiddleware:
    """
    Turns unexpected errors into a friendly page (or JSON for the API) with an occurrence code,
    and records the full context for support. With DEBUG on, the Django traceback page still shows.
    Kept last in MIDDLEWARE so it sees exceptions raised by the views.
    """
    EXPECTED = (Http404, PermissionDenied, BadRequest, SuspiciousOperation)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        capture_body(request)
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, self.EXPECTED):
            return None  # Django's own 404/403/400 handling (friendly pages in core/views.py)
        code = new_code()
        request._error_code = code
        record(request, exception, code)
        if settings.DEBUG:
            return None
        return error_response(request, 500, code=code)

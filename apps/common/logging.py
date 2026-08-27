import logging

from apps.common import request_context


class RequestIDLogFilter(logging.Filter):
    """Injects the current request's correlation id into every log record."""

    def filter(self, record):
        record.request_id = request_context.get_request_id()
        return True

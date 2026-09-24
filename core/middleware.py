import logging
import time
import uuid

from config.logging_utils import request_id_context


logger = logging.getLogger('portal.request')


class RequestContextMiddleware:
    """Asigna un ID único y registra duración y estado de cada solicitud."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = uuid.uuid4().hex
        request.request_id = request_id
        context_token = request_id_context.set(request_id)
        started_at = time.perf_counter()

        try:
            response = self.get_response(request)
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            response['X-Request-ID'] = request_id
            logger.info(
                'request_completed',
                extra={
                    'http_method': request.method,
                    'http_path': request.path,
                    'status_code': response.status_code,
                    'duration_ms': duration_ms,
                },
            )
            return response
        finally:
            request_id_context.reset(context_token)

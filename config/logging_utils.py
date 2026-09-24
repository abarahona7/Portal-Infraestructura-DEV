import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone


request_id_context = ContextVar('request_id', default='-')


class RequestIdFilter(logging.Filter):
    """Agrega el identificador de solicitud a todos los registros."""

    def filter(self, record):
        record.request_id = getattr(record, 'request_id', request_id_context.get())
        return True


class JsonFormatter(logging.Formatter):
    """Formato JSON estable sin datos de solicitudes ni credenciales."""

    EXTRA_FIELDS = (
        'request_id',
        'http_method',
        'http_path',
        'status_code',
        'duration_ms',
        'event',
        'reason',
    )

    def format(self, record):
        payload = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        for field in self.EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value not in (None, ''):
                payload[field] = value
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

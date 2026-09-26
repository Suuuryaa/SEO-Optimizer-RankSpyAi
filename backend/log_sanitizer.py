"""
Structured logging with automatic redaction of secrets and PII.
Install once at startup via configure_logging().
"""
import logging
import re
from urllib.parse import urlparse

_REDACT_PATTERNS = [
    (re.compile(r'AIzaSy[A-Za-z0-9_-]{33}'),                    '[GEMINI_KEY]'),
    (re.compile(r'\bre_[A-Za-z0-9_-]{32,}'),                    '[RESEND_KEY]'),
    (re.compile(r'(?i)(Bearer\s+)\S+'),                          r'\1[TOKEN]'),
    (re.compile(r'(?i)(apikey|api_key|x-api-key)([:=\s"\']+)\S+'), r'\1\2[REDACTED]'),
    (re.compile(r'(?i)(token|secret|password)([:=\s"\']+)\S+'),  r'\1\2[REDACTED]'),
    # Strip query params that may carry ?key=... from URLs in log messages
    (re.compile(r'(\?[^"\'>\s]*(?:key|token|secret|auth)[^"\'>\s]*)'), '[?REDACTED]'),
]


def sanitize(text: str) -> str:
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def safe_domain(url: str) -> str:
    """Return only the netloc of a URL — safe to log."""
    try:
        return urlparse(url).netloc or url[:50]
    except Exception:
        return "[url]"


class SanitizingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = sanitize(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: sanitize(str(v)) for k, v in record.args.items()}
            else:
                record.args = tuple(sanitize(str(a)) for a in record.args)
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.addFilter(SanitizingFilter())
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s',
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    ))
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers = [handler]

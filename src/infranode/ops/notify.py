"""Public-Stub: kein Notifier-Versand (ntfy/E-Mail) im oeffentlichen Build."""
from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


def notify(*args, **kwargs) -> None:
    """No-op: der oeffentliche Build versendet keine Betreiber-Benachrichtigungen."""

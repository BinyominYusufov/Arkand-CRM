"""Доменные ошибки и единый формат ответа об ошибке.

Формат (ТЗ, раздел 10): { "code": "...", "message": "...", "details": {...} }
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler


class DomainError(Exception):
    """Базовая доменная ошибка сервисного слоя."""

    code = "domain_error"
    http_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, *, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details or {}


class ConflictError(DomainError):
    """Операция уже выполнена / конфликт статусов (идемпотентность)."""

    code = "conflict"
    http_status = status.HTTP_409_CONFLICT


class LimitExceededError(DomainError):
    """Превышен лимит оборота кассы (КАС-03)."""

    code = "cash_limit_exceeded"
    http_status = status.HTTP_400_BAD_REQUEST


class InsufficientFundsError(DomainError):
    """Недостаточно средств в кассе для расходной операции."""

    code = "insufficient_funds"
    http_status = status.HTTP_400_BAD_REQUEST


class NotAllowedError(DomainError):
    """Действие запрещено бизнес-правилом."""

    code = "not_allowed"
    http_status = status.HTTP_403_FORBIDDEN


class NotFoundError(DomainError):
    """Объект не найден или недоступен."""

    code = "not_found"
    http_status = status.HTTP_404_NOT_FOUND


def _error_payload(code: str, message: str, details=None) -> dict:
    return {"code": code, "message": message, "details": details or {}}


def drf_exception_handler(exc, context):
    """Приводит все ошибки API к единому формату."""
    if isinstance(exc, DomainError):
        return Response(
            _error_payload(exc.code, exc.message, exc.details),
            status=exc.http_status,
        )

    response = drf_default_handler(exc, context)
    if response is None:
        return None  # 500 — стандартная обработка Django

    from rest_framework.exceptions import (
        AuthenticationFailed,
        NotAuthenticated,
        NotFound,
        PermissionDenied,
        ValidationError,
    )

    if isinstance(exc, ValidationError):
        payload = _error_payload("validation_error", "Некорректные данные", response.data)
    elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        payload = _error_payload("not_authenticated", "Требуется аутентификация", response.data)
    elif isinstance(exc, PermissionDenied):
        payload = _error_payload("permission_denied", "Недостаточно прав", response.data)
    elif isinstance(exc, NotFound) or response.status_code == status.HTTP_404_NOT_FOUND:
        # django.http.Http404 (get_object_or_404) не является DRF NotFound —
        # ловим по статусу, чтобы формат 404 был единым.
        payload = _error_payload("not_found", "Объект не найден", {})
    else:
        detail = getattr(exc, "detail", str(exc))
        payload = _error_payload("error", str(detail), {})

    response.data = payload
    return response

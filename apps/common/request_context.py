"""
Per-request state shared between middleware, the structured logging filter,
and the audit service, without threading a request object through every
function call.
"""

import contextvars
import uuid

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
_current_user_id: contextvars.ContextVar[int | None] = contextvars.ContextVar("current_user_id", default=None)
_client_ip: contextvars.ContextVar[str | None] = contextvars.ContextVar("client_ip", default=None)


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> str:
    return _request_id.get()


def set_current_user_id(value: int | None) -> None:
    _current_user_id.set(value)


def get_current_user_id() -> int | None:
    return _current_user_id.get()


def set_client_ip(value: str | None) -> None:
    _client_ip.set(value)


def get_client_ip() -> str | None:
    return _client_ip.get()

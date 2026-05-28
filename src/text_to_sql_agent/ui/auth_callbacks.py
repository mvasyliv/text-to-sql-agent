"""Chainlit authentication callback wiring for username/password login.

This module provides:

- ``build_auth_service_from_env()`` — factory that wires ``AuthService`` from
  environment config; re-used on every server startup.
- ``authenticate_with_password()`` — pure async function that calls the auth
  service and returns an ``AuthPrincipal`` or ``None``; kept independent of
  Chainlit so it can be unit-tested without a running server.

The ``@cl.password_auth_callback`` decorator is registered in
``chainlit_app.py`` to keep Chainlit-specific wiring in one place.
"""

from __future__ import annotations

import os

from text_to_sql_agent.config.settings import (
    ConversationAuthSettings,
    load_conversation_auth_settings,
)
from text_to_sql_agent.models.auth import AuthPrincipal, UserLogin
from text_to_sql_agent.repositories.sqlite_auth_repository import SQLiteAuthRepository
from text_to_sql_agent.services.auth_service import AuthError, AuthService


def build_auth_service_from_env(
    settings: ConversationAuthSettings | None = None,
) -> AuthService:
    """Build an ``AuthService`` wired to the conversation SQLite database.

    Reads ``CONVERSATION_DB_PATH`` (and related auth policy flags) from the
    process environment via ``load_conversation_auth_settings()``.

    Args:
        settings: Explicit settings override; defaults to env-loaded values.

    Returns:
        A ready-to-use ``AuthService`` instance.
    """
    resolved = settings or load_conversation_auth_settings()
    repo = SQLiteAuthRepository(resolved.conversation_db_path)
    return AuthService(auth_repo=repo, settings=resolved)


async def authenticate_with_password(
    username: str,
    password: str,
    auth_service: AuthService,
) -> AuthPrincipal | None:
    """Authenticate or auto-register a user by username and password.

    This function is the testable core of the Chainlit password auth callback.
    It is intentionally free of any Chainlit imports so it can be exercised in
    isolation.

    Args:
        username: Login name submitted by the user.
        password: Plain-text password submitted by the user.
        auth_service: ``AuthService`` instance used for verification.

    Returns:
        ``AuthPrincipal`` on success, ``None`` when authentication fails.
    """
    try:
        result = auth_service.authenticate_or_register(
            UserLogin(username=username, password=password)
        )
        return result.principal
    except AuthError:
        return None


def make_chainlit_user(principal: AuthPrincipal):  # type: ignore[return]
    """Convert an ``AuthPrincipal`` to a ``chainlit.User`` instance.

    Imports Chainlit lazily so that this module remains importable in test
    environments where Chainlit is not running.

    Args:
        principal: Authenticated user principal.

    Returns:
        ``chainlit.User`` with ``identifier``, ``display_name``, and ``metadata``.
    """
    try:
        import chainlit as cl  # noqa: PLC0415

        return cl.User(
            identifier=principal.user_id,
            display_name=principal.display_name,
            metadata={"username": principal.username},
        )
    except ModuleNotFoundError:  # pragma: no cover
        return None


"""Authentication service: register-or-login policy, password hashing, and verification.

Responsibilities
----------------
- Hash plain-text passwords with Argon2id before storage.
- Verify a submitted password against a stored hash.
- Implement the register-or-login policy:
    * When ``AUTH_AUTO_REGISTER_ON_FIRST_LOGIN`` is enabled (default), the first
      login attempt with an unknown username creates a new account automatically.
    * When the flag is disabled, unknown usernames return an authentication error.
- Enforce the minimum password length from ``ConversationAuthSettings``.
- Reject login attempts for inactive accounts.

Returns ``AuthPrincipal`` on success, raises ``AuthError`` on failure.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from text_to_sql_agent.config.settings import ConversationAuthSettings, load_conversation_auth_settings
from text_to_sql_agent.models.auth import AuthPrincipal, UserAccount, UserLogin, UserRegistration
from text_to_sql_agent.repositories.sqlite_auth_repository import SQLiteAuthRepository

# Shared Argon2id hasher with secure defaults.
_hasher = PasswordHasher()


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------

class AuthError(Exception):
    """Raised when authentication or registration fails."""


# ---------------------------------------------------------------------------
# Auth result
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AuthResult:
    """Outcome of a successful authenticate_or_register call."""

    principal: AuthPrincipal
    registered: bool  # True when a new account was created during this call


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Hash ``plain`` with Argon2id and return the encoded hash string."""
    return _hasher.hash(plain)


def verify_password(plain: str, stored_hash: str) -> bool:
    """Return ``True`` when ``plain`` matches ``stored_hash``, ``False`` otherwise."""
    try:
        return _hasher.verify(stored_hash, plain)
    except (VerifyMismatchError, VerificationError):
        return False


# ---------------------------------------------------------------------------
# Auth service
# ---------------------------------------------------------------------------

class AuthService:
    """High-level authentication service.

    Args:
        auth_repo:  Repository for reading and writing ``UserAccount`` records.
        settings:   Auth policy flags (min password length, auto-register).
                    Defaults to values loaded from the process environment.
    """

    def __init__(
        self,
        auth_repo: SQLiteAuthRepository,
        settings: ConversationAuthSettings | None = None,
    ) -> None:
        self._repo = auth_repo
        self._settings = settings or load_conversation_auth_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def authenticate_or_register(self, login: UserLogin) -> AuthResult:
        """Authenticate an existing user or register a new one.

        Behaviour depends on ``settings.auth_auto_register_on_first_login``:

        - **auto-register ON** (default): unknown username → new account created
          with the submitted password.  The same call then succeeds and returns
          ``AuthResult(registered=True)``.
        - **auto-register OFF**: unknown username → ``AuthError``.

        In both modes, inactive accounts always raise ``AuthError``.

        Args:
            login: ``UserLogin`` payload with ``username`` and ``password``.

        Returns:
            ``AuthResult`` with the authenticated ``AuthPrincipal``.

        Raises:
            AuthError: on wrong password, inactive account, policy violation,
                       or missing account when auto-register is disabled.
        """
        account = self._repo.get_by_username(login.username)

        if account is None:
            if not self._settings.auth_auto_register_on_first_login:
                raise AuthError(f"Unknown username: '{login.username}'.")
            # Auto-register path
            reg = UserRegistration(username=login.username, password=login.password)
            return self._register(reg)

        # Existing account — verify password
        if not verify_password(login.password, account.password_hash):
            raise AuthError("Invalid password.")

        if not account.is_active:
            raise AuthError(f"Account '{login.username}' is disabled.")

        return AuthResult(principal=AuthPrincipal.from_account(account), registered=False)

    def register(self, registration: UserRegistration) -> AuthResult:
        """Explicitly register a new user account.

        Unlike ``authenticate_or_register``, this always creates a new account
        and fails if the username is already taken.

        Args:
            registration: ``UserRegistration`` payload.

        Returns:
            ``AuthResult(registered=True)`` on success.

        Raises:
            AuthError: if username is taken or password is below minimum length.
        """
        if self._repo.username_exists(registration.username):
            raise AuthError(f"Username '{registration.username}' is already taken.")
        return self._register(registration)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _register(self, reg: UserRegistration) -> AuthResult:
        """Validate, hash, persist, and return a new account."""
        min_len = self._settings.auth_min_password_length
        if len(reg.password) < min_len:
            raise AuthError(
                f"Password must be at least {min_len} characters long."
            )

        account = UserAccount(
            user_id=f"u-{uuid4().hex}",
            username=reg.username,
            password_hash=hash_password(reg.password),
            display_name=reg.resolved_display_name(),
        )
        self._repo.create_account(account)
        return AuthResult(principal=AuthPrincipal.from_account(account), registered=True)


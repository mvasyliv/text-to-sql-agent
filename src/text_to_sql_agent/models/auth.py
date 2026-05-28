"""Authentication-focused data models for username/password flow.

Covers:
- ``UserAccount``     – the persisted record stored in the conversation database.
- ``UserRegistration`` – validated payload for creating a new account.
- ``UserLogin``       – validated payload for a login attempt.
- ``AuthPrincipal``   – lightweight identity returned after successful authentication.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserAccount(BaseModel):
    """Persisted user account record stored in the conversation database.

    ``password_hash`` must never hold a plain-text password; the auth service
    is responsible for hashing before creating or updating this record.
    """

    user_id: str = Field(description="Stable unique identifier (UUID or slug).")
    username: str = Field(description="Unique login name chosen by the user.")
    password_hash: str = Field(description="Argon2 or bcrypt hash of the password.")
    display_name: str = Field(description="Human-readable name shown in the UI.")
    is_active: bool = Field(
        default=True,
        description="False when the account is disabled or soft-deleted.",
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        description="Timestamp when the account was first created.",
    )
    updated_at: datetime = Field(
        default_factory=_utcnow,
        description="Timestamp of the last account modification.",
    )


class UserRegistration(BaseModel):
    """Payload submitted when a new user registers.

    Validation enforces a minimum password length and strips surrounding
    whitespace from the username.  The auth service applies the password
    policy defined in ``ConversationAuthSettings`` before persisting.
    """

    username: str = Field(
        min_length=1,
        description="Desired login name.  Must be unique across all accounts.",
    )
    password: str = Field(
        min_length=1,
        description="Plain-text password supplied by the user (never stored as-is).",
    )
    display_name: str = Field(
        default="",
        description="Optional display name; falls back to ``username`` when blank.",
    )

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, v: str) -> str:
        return v.strip()

    @field_validator("display_name", mode="before")
    @classmethod
    def default_display_name(cls, v: str) -> str:
        return v.strip()

    def resolved_display_name(self) -> str:
        """Return display_name if set, otherwise fall back to username."""
        return self.display_name or self.username


class UserLogin(BaseModel):
    """Payload submitted when a user attempts to log in."""

    username: str = Field(description="Login name of the existing account.")
    password: str = Field(description="Plain-text password for verification.")

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, v: str) -> str:
        return v.strip()


class AuthPrincipal(BaseModel):
    """Lightweight identity object returned after a successful login.

    Passed into Chainlit user session and used throughout the UI layer.
    Does **not** contain the password hash.
    """

    user_id: str = Field(description="Stable unique identifier for the user.")
    username: str = Field(description="Login name of the authenticated user.")
    display_name: str = Field(description="Human-readable name for UI display.")
    is_active: bool = Field(default=True)

    @classmethod
    def from_account(cls, account: UserAccount) -> "AuthPrincipal":
        """Build an ``AuthPrincipal`` from a ``UserAccount`` record."""
        return cls(
            user_id=account.user_id,
            username=account.username,
            display_name=account.display_name,
            is_active=account.is_active,
        )


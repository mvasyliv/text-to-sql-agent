"""SQLite-backed repository for user account authentication data.

Handles all CRUD operations for ``UserAccount`` records stored in the
``users`` table of the conversation database.  Password hashing is the
responsibility of the auth service — this repository stores and retrieves
pre-hashed values only.

Public API
----------
- ``create_account(account)``    — insert a new user account.
- ``get_by_username(username)``  — look up an account by login name.
- ``get_by_user_id(user_id)``   — look up an account by stable ID.
- ``update_password_hash(user_id, new_hash)``  — replace stored hash.
- ``set_active(user_id, is_active)``           — toggle account status.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from text_to_sql_agent.models.auth import UserAccount
from text_to_sql_agent.repositories.conversation_db import bootstrap_schema, managed_connection


# ---------------------------------------------------------------------------
# Datetime helpers
# ---------------------------------------------------------------------------

def _dt_to_str(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _str_to_dt(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class SQLiteAuthRepository:
    """Persistent auth repository backed by the conversation SQLite database.

    The database schema is bootstrapped automatically on first instantiation.

    Args:
        db_path: Path to the SQLite file used for auth persistence.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        bootstrap_schema(self._db_path)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def create_account(self, account: UserAccount) -> None:
        """Insert a new user account.

        Raises:
            ValueError: if ``username`` or ``user_id`` already exists.
        """
        try:
            with managed_connection(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO users
                        (user_id, username, password_hash, display_name,
                         is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        account.user_id,
                        account.username,
                        account.password_hash,
                        account.display_name,
                        int(account.is_active),
                        _dt_to_str(account.created_at),
                        _dt_to_str(account.updated_at),
                    ),
                )
                conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"Account with username '{account.username}' or "
                f"user_id '{account.user_id}' already exists."
            ) from exc

    def update_password_hash(self, user_id: str, new_hash: str) -> None:
        """Replace the stored password hash for the given user.

        Raises:
            ValueError: if no account with ``user_id`` exists.
        """
        now = _dt_to_str(datetime.now(timezone.utc))
        with managed_connection(self._db_path) as conn:
            cursor = conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?",
                (new_hash, now, user_id),
            )
            conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"No account found for user_id '{user_id}'.")

    def set_active(self, user_id: str, *, is_active: bool) -> None:
        """Enable or disable an account without deleting it.

        Raises:
            ValueError: if no account with ``user_id`` exists.
        """
        now = _dt_to_str(datetime.now(timezone.utc))
        with managed_connection(self._db_path) as conn:
            cursor = conn.execute(
                "UPDATE users SET is_active = ?, updated_at = ? WHERE user_id = ?",
                (int(is_active), now, user_id),
            )
            conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"No account found for user_id '{user_id}'.")

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_by_username(self, username: str) -> UserAccount | None:
        """Return the account with the given username, or ``None``."""
        with managed_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
        return _row_to_account(row) if row else None

    def get_by_user_id(self, user_id: str) -> UserAccount | None:
        """Return the account with the given user_id, or ``None``."""
        with managed_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
        return _row_to_account(row) if row else None

    def username_exists(self, username: str) -> bool:
        """Return ``True`` if ``username`` is already registered."""
        with managed_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM users WHERE username = ? LIMIT 1", (username,)
            ).fetchone()
        return row is not None


# ---------------------------------------------------------------------------
# Row → model helper
# ---------------------------------------------------------------------------

def _row_to_account(row) -> UserAccount:
    return UserAccount(
        user_id=row["user_id"],
        username=row["username"],
        password_hash=row["password_hash"],
        display_name=row["display_name"] or "",
        is_active=bool(row["is_active"]),
        created_at=_str_to_dt(row["created_at"]),
        updated_at=_str_to_dt(row["updated_at"]),
    )


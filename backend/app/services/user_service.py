"""
User service.

Business logic for user registration, authentication, and user lookup.
Contains no HTTP concerns.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserLoginRequest, UserRegisterRequest

logger = logging.getLogger(__name__)


# ── Domain Exceptions ─────────────────────────────────────────────────────────

class UserError(Exception):
    """Base domain exception for user service errors."""
    pass


class DuplicateEmailError(UserError):
    """Raised when registering an email that already exists."""
    pass


class InvalidCredentialsError(UserError):
    """Raised when email or password authentication fails."""
    pass


class InactiveUserError(UserError):
    """Raised when an inactive user attempts to authenticate."""
    pass


class GoogleAccountConflictError(UserError):
    """Raised when a Google identity conflicts with an existing account."""
    pass


class UnverifiedEmailError(UserError):
    """Raised when attempting to authenticate with an unverified email."""
    pass


# ── Service ───────────────────────────────────────────────────────────────────

class UserService:
    """
    Service layer for user account operations.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def register_user(self, data: UserRegisterRequest) -> User:
        """
        Register a new user account.

        Validates uniqueness of email, hashes the password using Argon2id,
        inserts the User row, and commits the transaction.

        Raises:
            DuplicateEmailError: if an account with the normalized email exists.
            ValueError: if input validation fails (e.g. empty password).
        """
        normalized_email = data.email.strip().lower()

        if self.get_by_email(normalized_email) is not None:
            logger.info("Registration failed — duplicate email")
            raise DuplicateEmailError(f"An account with email '{normalized_email}' already exists")

        pw_hash = hash_password(data.password)
        now = datetime.now(UTC)

        user = User(
            id=uuid.uuid4(),
            name=data.name.strip(),
            email=normalized_email,
            password_hash=pw_hash,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)

        logger.info("Successfully registered user id=%s", user.id)
        return user

    def authenticate_user(self, data: UserLoginRequest) -> User:
        """
        Authenticate a user by email and password.

        Raises:
            InvalidCredentialsError: if email is not found or password is incorrect.
            InactiveUserError: if the user account is disabled/inactive.
        """
        normalized_email = data.email.strip().lower()
        user = self.get_by_email(normalized_email)

        if user is None or user.password_hash is None or not verify_password(data.password, user.password_hash):
            logger.info("Authentication failed — invalid credentials")
            raise InvalidCredentialsError("Invalid email or password")

        if not user.is_active:
            logger.warning("Authentication failed — inactive user id=%s", user.id)
            raise InactiveUserError("User account is inactive")

        logger.info("Successfully authenticated user id=%s", user.id)
        return user

    def get_by_email(self, email: str) -> User | None:
        """Fetch a User by normalized email, or None if not found."""
        stmt = select(User).where(User.email == email.strip().lower())
        return self._db.execute(stmt).scalar_one_or_none()

    def get_by_google_id(self, google_id: str) -> User | None:
        """Fetch a User by Google subject identifier, or None if not found."""
        if not google_id or not google_id.strip():
            return None
        stmt = select(User).where(User.google_id == google_id.strip())
        return self._db.execute(stmt).scalar_one_or_none()

    def authenticate_or_create_google_user(
        self,
        google_id: str,
        email: str,
        name: str,
    ) -> User:
        """
        Authenticate or provision a user from verified Google identity data.

        Handles 3 cases:
        1. User with matching google_id exists:
           Validates active status and returns existing user.
        2. User with matching email exists:
           Safe account linking: if user has no google_id, links it;
           if already linked to a different google_id, raises GoogleAccountConflictError.
           Preserves existing password_hash.
        3. Completely new user:
           Creates a new active User row with password_hash=None and google_id set.

        Raises:
            InactiveUserError: if the user account is disabled.
            GoogleAccountConflictError: if the email is linked to another Google ID.
        """
        if not google_id or not google_id.strip():
            raise ValueError("google_id must not be empty")
        if not email or not email.strip():
            raise ValueError("email must not be empty")

        clean_google_id = google_id.strip()
        normalized_email = email.strip().lower()
        clean_name = name.strip() or "Google User"
        now = datetime.now(UTC)

        # Case 1: Existing Google user
        existing_by_google = self.get_by_google_id(clean_google_id)
        if existing_by_google is not None:
            if not existing_by_google.is_active:
                logger.warning("Google authentication failed — inactive user id=%s", existing_by_google.id)
                raise InactiveUserError("User account is inactive")
            logger.info("Successfully authenticated existing Google user id=%s", existing_by_google.id)
            return existing_by_google

        # Case 2: Existing email/password user (Account Linking)
        existing_by_email = self.get_by_email(normalized_email)
        if existing_by_email is not None:
            if not existing_by_email.is_active:
                logger.warning("Google authentication failed — inactive user id=%s", existing_by_email.id)
                raise InactiveUserError("User account is inactive")

            if existing_by_email.google_id is not None and existing_by_email.google_id != clean_google_id:
                logger.warning(
                    "Google account linking conflict for email=%s (existing google_id != incoming)",
                    normalized_email,
                )
                raise GoogleAccountConflictError(
                    "An account with this email is already linked to a different Google account."
                )

            # Link Google identity to existing account, keeping existing password_hash intact
            existing_by_email.google_id = clean_google_id
            existing_by_email.updated_at = now
            self._db.commit()
            self._db.refresh(existing_by_email)
            logger.info(
                "Successfully linked Google account to existing user id=%s",
                existing_by_email.id,
            )
            return existing_by_email

        # Case 3: Completely new user
        new_user = User(
            id=uuid.uuid4(),
            name=clean_name,
            email=normalized_email,
            password_hash=None,
            google_id=clean_google_id,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._db.add(new_user)
        self._db.commit()
        self._db.refresh(new_user)
        logger.info("Successfully registered new user via Google id=%s", new_user.id)
        return new_user

    def get_by_id(self, user_id: uuid.UUID | str) -> User | None:
        """Fetch a User by ID UUID/string, or None if not found."""
        if isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except ValueError:
                return None
        return self._db.get(User, user_id)

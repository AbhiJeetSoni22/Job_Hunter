"""
User service.

Business logic for user registration, authentication, and user lookup.
Contains no HTTP concerns.
"""

import logging
import uuid
from datetime import datetime, timezone

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
            logger.info("Registration failed — email already exists: %s", normalized_email)
            raise DuplicateEmailError(f"An account with email '{normalized_email}' already exists")

        pw_hash = hash_password(data.password)
        now = datetime.now(timezone.utc)

        user = User(
            id=str(uuid.uuid4()),
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

        logger.info("Successfully registered user id=%s email=%s", user.id, user.email)
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

        if user is None:
            logger.info("Auth failed — user not found for email: %s", normalized_email)
            raise InvalidCredentialsError("Invalid email or password")

        if not verify_password(data.password, user.password_hash):
            logger.info("Auth failed — password mismatch for user id=%s", user.id)
            raise InvalidCredentialsError("Invalid email or password")

        if not user.is_active:
            logger.warning("Auth failed — inactive user id=%s", user.id)
            raise InactiveUserError("User account is inactive")

        logger.info("Successfully authenticated user id=%s", user.id)
        return user

    def get_by_email(self, email: str) -> User | None:
        """Fetch a User by normalized email, or None if not found."""
        stmt = select(User).where(User.email == email.strip().lower())
        return self._db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, user_id: uuid.UUID | str) -> User | None:
        """Fetch a User by ID UUID/string, or None if not found."""
        return self._db.get(User, str(user_id))

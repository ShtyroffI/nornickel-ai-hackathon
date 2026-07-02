"""Ролевая модель, JWT, аудит действий."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.sql.audit import AuditLog
from app.models.sql.user import Role, User


class SecurityService:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return self.pwd_context.verify(plain, hashed)

    def create_access_token(self, subject: str, role: Role) -> tuple[str, int]:
        settings = get_settings()
        expires_minutes = settings.jwt_expires_minutes
        expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
        payload: dict[str, Any] = {"sub": subject, "role": role.value, "exp": expire}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        return token, expires_minutes * 60

    def decode_token(self, token: str) -> dict[str, Any]:
        settings = get_settings()
        try:
            return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        except JWTError as exc:
            raise ValueError("Invalid token") from exc

    def authenticate(self, db: Session, email: str, password: str) -> User | None:
        user = db.query(User).filter(User.email == email).first()
        if not user or not self.verify_password(password, user.hashed_password):
            return None
        return user

    def log(self, db: Session, user_id: int | None, action: str, entity_type: str | None, entity_id: str | None, payload: dict | None = None) -> None:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
        db.add(entry)
        db.commit()

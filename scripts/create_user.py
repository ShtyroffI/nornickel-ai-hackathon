"""CLI: создание администратора и базовых ролей."""

from __future__ import annotations

import argparse
import sys

from app.db.sql.session import SessionLocal
from app.logging_config import setup_logging
from app.models.sql.user import Role, User
from app.services.security.service import SecurityService


def main() -> int:
    parser = argparse.ArgumentParser(description="Создать пользователя")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", default=Role.RESEARCHER.value, choices=[r.value for r in Role])
    args = parser.parse_args()

    setup_logging()
    security = SecurityService()
    with SessionLocal() as db:
        if db.query(User).filter(User.email == args.email).first():
            print("User already exists")
            return 0
        user = User(
            email=args.email,
            full_name=args.full_name,
            hashed_password=security.hash_password(args.password),
            role=Role(args.role),
        )
        db.add(user)
        db.commit()
        print(f"OK user_id={user.id} role={user.role.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

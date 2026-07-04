import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.sql.session import Base


class Role(str, enum.Enum):
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    PROJECT_LEAD = "project_lead"
    ADMIN = "admin"
    EXTERNAL_PARTNER = "external_partner"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, values_callable=lambda obj: [e.value for e in obj]), default=Role.RESEARCHER, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")

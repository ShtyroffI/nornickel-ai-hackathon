from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import security
from app.db.sql.session import get_db
from app.schemas.auth import TokenResponse


router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    user = security.authenticate(db, form.username, form.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token, expires_in = security.create_access_token(user.email, user.role)
    security.log(db, user.id, "login", "user", str(user.id))
    return TokenResponse(access_token=token, expires_in=expires_in)

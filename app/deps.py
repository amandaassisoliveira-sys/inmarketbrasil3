from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from .db import get_db
from . import models
from .auth_utils import decode_access_token


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Não autenticado. Faça login para continuar.")
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada. Faça login novamente.")
    user = db.query(models.User).filter(models.User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")
    return user

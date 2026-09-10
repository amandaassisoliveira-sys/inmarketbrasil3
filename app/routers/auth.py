import secrets
import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth_utils import create_access_token
from ..email_utils import enviar_link_magico
from ..config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class RequestLinkBody(BaseModel):
    email: EmailStr


@router.post("/request-link")
async def request_link(body: RequestLinkBody, db: Session = Depends(get_db)):
    email = body.email.lower()
    token = secrets.token_urlsafe(32)
    expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)

    link = models.MagicLink(email=email, token=token, expires_at=expires, used=False)
    db.add(link)
    db.commit()

    await enviar_link_magico(email, token)

    resposta = {"message": "Enviamos um link de acesso para o seu email. Confira também o spam."}
    # Em modo de desenvolvimento (sem RESEND_API_KEY configurada), devolvemos o token
    # direto na resposta, só para facilitar testar o fluxo sem precisar configurar email ainda.
    # Isso desaparece automaticamente assim que RESEND_API_KEY for configurada de verdade.
    if not settings.RESEND_API_KEY:
        resposta["dev_verify_url"] = f"{settings.SITE_URL}/?login_token={token}"
    return resposta


@router.get("/verify")
def verify(token: str, db: Session = Depends(get_db)):
    link = db.query(models.MagicLink).filter(models.MagicLink.token == token).first()
    if not link or link.used or link.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=400, detail="Link inválido ou expirado. Peça um novo link de acesso.")

    link.used = True

    user = db.query(models.User).filter(models.User.email == link.email).first()
    if not user:
        user = models.User(email=link.email)
        db.add(user)
        db.flush()

    db.commit()

    access_token = create_access_token(user.id, user.email)
    return {"access_token": access_token, "token_type": "bearer", "email": user.email}

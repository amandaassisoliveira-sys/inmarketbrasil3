import secrets
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..deps import get_current_user
from ..config import settings

router = APIRouter(prefix="/simulations", tags=["simulations"])


class SalvarSimulacaoBody(BaseModel):
    nome: str = ""
    data: Dict[str, Any]  # o estado inteiro da simulação (produto, pesos, resultado, etc.)


def gerar_codigo() -> str:
    return "SIM-" + secrets.token_hex(3).upper()


@router.post("")
def salvar_simulacao(body: SalvarSimulacaoBody, user=Depends(get_current_user), db: Session = Depends(get_db)):
    total = db.query(models.Simulation).filter(models.Simulation.user_id == user.id).count()
    if total >= settings.LIMITE_SIMULACOES_POR_USUARIO:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Você atingiu o limite de {settings.LIMITE_SIMULACOES_POR_USUARIO} simulações salvas. "
                "Apague alguma antes de salvar uma nova."
            ),
        )
    codigo = gerar_codigo()
    sim = models.Simulation(user_id=user.id, code=codigo, nome=body.nome, data=json.dumps(body.data))
    db.add(sim)
    db.commit()
    return {"code": codigo, "message": "Simulação salva com sucesso."}


@router.get("")
def listar_simulacoes(user=Depends(get_current_user), db: Session = Depends(get_db)):
    sims = (
        db.query(models.Simulation)
        .filter(models.Simulation.user_id == user.id)
        .order_by(models.Simulation.created_at.desc())
        .all()
    )
    return [
        {"code": s.code, "nome": s.nome, "created_at": s.created_at.isoformat()}
        for s in sims
    ]


@router.get("/{code}")
def obter_simulacao(code: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    sim = (
        db.query(models.Simulation)
        .filter(models.Simulation.user_id == user.id, models.Simulation.code == code)
        .first()
    )
    if not sim:
        raise HTTPException(status_code=404, detail="Simulação não encontrada.")
    return {
        "code": sim.code,
        "nome": sim.nome,
        "data": json.loads(sim.data),
        "created_at": sim.created_at.isoformat(),
    }


@router.delete("/{code}")
def apagar_simulacao(code: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    sim = (
        db.query(models.Simulation)
        .filter(models.Simulation.user_id == user.id, models.Simulation.code == code)
        .first()
    )
    if not sim:
        raise HTTPException(status_code=404, detail="Simulação não encontrada.")
    db.delete(sim)
    db.commit()
    return {"message": "Simulação apagada."}

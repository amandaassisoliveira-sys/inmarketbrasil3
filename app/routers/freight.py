import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from ..services.ups import quote_ups
from ..services.dhl import quote_dhl
from ..services.fedex import quote_fedex

router = APIRouter(prefix="/freight", tags=["freight"])


class FreightRequest(BaseModel):
    peso_kg: float
    comprimento_cm: float = 0
    largura_cm: float = 0
    altura_cm: float = 0
    peso_cubado_kg: float = 0  # soma pré-calculada da cubagem de todas as caixas (preferencial)
    origem: str
    destino: str = "BR"
    valor_usd: float
    cep_origem: str = ""
    cep_destino: str = ""
    qtd_caixas: int = 1


def peso_taxavel(peso_real, c, l, a, qtd_caixas=1, peso_cubado_pronto=0):
    if peso_cubado_pronto > 0:
        volumetrico = peso_cubado_pronto
    else:
        volumetrico = ((c * l * a) / 5000) * max(qtd_caixas, 1)
    return max(peso_real, volumetrico)


@router.post("/quote")
async def get_freight_quotes(req: FreightRequest):
    peso = peso_taxavel(req.peso_kg, req.comprimento_cm, req.largura_cm, req.altura_cm,
                         req.qtd_caixas, req.peso_cubado_kg)

    resultados = await asyncio.gather(
        quote_ups(peso, req.origem, req.destino, req.valor_usd, req.cep_origem, req.cep_destino),
        quote_dhl(peso, req.origem, req.destino, req.valor_usd, req.cep_origem, req.cep_destino),
        quote_fedex(peso, req.origem, req.destino, req.valor_usd, req.cep_origem, req.cep_destino),
        return_exceptions=True,
    )

    cotacoes = []
    for r in resultados:
        if isinstance(r, Exception):
            cotacoes.append({"error": str(r)})
        else:
            cotacoes.append(r)

    validas = [c for c in cotacoes if "price_usd" in c]
    mais_barata = min(validas, key=lambda c: c["price_usd"]) if validas else None

    return {
        "peso_taxavel_kg": round(peso, 2),
        "cotacoes": cotacoes,
        "mais_barata": mais_barata["carrier"] if mais_barata else None,
    }

import httpx
import base64
from ..config import settings


async def quote_dhl(peso_kg: float, origem: str, destino: str, valor_usd: float,
                     cep_origem: str = "", cep_destino: str = "") -> dict:
    if settings.MOCK_MODE:
        base, per_kg = 110, 44
        preco = base + per_kg * max(peso_kg, 0.5)
        return {"carrier": "DHL", "price_usd": round(preco, 2), "eta_days": "3-5", "source": "mock"}

    credentials = base64.b64encode(f"{settings.DHL_API_KEY}:{settings.DHL_API_SECRET}".encode()).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.DHL_BASE_URL}/rates",
            headers={"Authorization": f"Basic {credentials}"},
            params={
                "originCountryCode": origem,
                "originPostalCode": cep_origem,
                "destinationCountryCode": destino,
                "destinationPostalCode": cep_destino,
                "weight": peso_kg,
                "isCustomsDeclarable": "true",
                "unitOfMeasurement": "metric",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        # TODO: confirmar o campo exato do valor total assim que houver credencial real
        preco = float(data["products"][0]["totalPrice"][0]["price"])
        return {"carrier": "DHL", "price_usd": preco, "eta_days": None, "source": "live"}

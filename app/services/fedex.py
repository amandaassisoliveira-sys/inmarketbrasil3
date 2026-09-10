import httpx
from ..config import settings

_token_cache = {"access_token": None}


async def get_fedex_token() -> str:
    if _token_cache["access_token"]:
        return _token_cache["access_token"]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.FEDEX_BASE_URL}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.FEDEX_CLIENT_ID,
                "client_secret": settings.FEDEX_CLIENT_SECRET,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["access_token"] = data["access_token"]
        return data["access_token"]


async def quote_fedex(peso_kg: float, origem: str, destino: str, valor_usd: float,
                       cep_origem: str = "", cep_destino: str = "") -> dict:
    if settings.MOCK_MODE:
        base, per_kg = 105, 41
        preco = base + per_kg * max(peso_kg, 0.5)
        return {"carrier": "FedEx", "price_usd": round(preco, 2), "eta_days": "4-6", "source": "mock"}

    token = await get_fedex_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.FEDEX_BASE_URL}/rate/v1/rates/quotes",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "requestedShipment": {
                    "shipper": {"address": {"countryCode": origem, "postalCode": cep_origem}},
                    "recipient": {"address": {"countryCode": destino, "postalCode": cep_destino}},
                    "requestedPackageLineItems": [{"weight": {"units": "KG", "value": peso_kg}}],
                }
            },
        )
        resp.raise_for_status()
        data = resp.json()
        # TODO: confirmar o campo exato do valor total assim que houver credencial real
        preco = float(data["output"]["rateReplyDetails"][0]["ratedShipmentDetails"][0]["totalNetCharge"])
        return {"carrier": "FedEx", "price_usd": preco, "eta_days": None, "source": "live"}

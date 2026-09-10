import httpx
from ..config import settings

_token_cache = {"access_token": None}


async def get_ups_token() -> str:
    if _token_cache["access_token"]:
        return _token_cache["access_token"]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.UPS_BASE_URL}/security/v1/oauth/token",
            data={"grant_type": "client_credentials"},
            auth=(settings.UPS_CLIENT_ID, settings.UPS_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["access_token"] = data["access_token"]
        return data["access_token"]


async def quote_ups(peso_kg: float, origem: str, destino: str, valor_usd: float,
                     cep_origem: str = "", cep_destino: str = "") -> dict:
    if settings.MOCK_MODE:
        base, per_kg = 95, 38
        preco = base + per_kg * max(peso_kg, 0.5)
        return {"carrier": "UPS", "price_usd": round(preco, 2), "eta_days": "5-7", "source": "mock"}

    token = await get_ups_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.UPS_BASE_URL}/rating/v1/Shop",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "RateRequest": {
                    "Shipment": {
                        "Shipper": {"Address": {"CountryCode": origem, "PostalCode": cep_origem}},
                        "ShipTo": {"Address": {"CountryCode": destino, "PostalCode": cep_destino}},
                        "Package": {"PackageWeight": {"UnitOfMeasurement": {"Code": "KGS"}, "Weight": str(peso_kg)}},
                    }
                }
            },
        )
        resp.raise_for_status()
        data = resp.json()
        # TODO: confirmar o campo exato do valor total assim que houver credencial real
        preco = float(data["RateResponse"]["RatedShipment"][0]["TotalCharges"]["MonetaryValue"])
        return {"carrier": "UPS", "price_usd": preco, "eta_days": None, "source": "live"}
